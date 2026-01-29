import os
import uuid
import logging
import requests
import shutil
import re
from sqlalchemy import select, update, insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import DiscoveredArtifact, CutoffOutcome, SeatPolicyQuarantine, CollegeCandidate
from app.services.registry_service import RegistryService, RegistryMode
from ingestion.common.services.context_manager import ContextManager, PolicyViolationError
from ingestion.cutoff_ingestion.plugins.kcet.adapter import KCETContextAdapter
from ingestion.cutoff_ingestion.plugins.kcet.table_parser import KCETTableParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Phase7_Orchestrator")

class ArtifactProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.registry = RegistryService()
        self.context_manager = ContextManager(self.registry)
        self.adapter = KCETContextAdapter()
        self.temp_dir = "./temp_downloads"
        os.makedirs(self.temp_dir, exist_ok=True)
        # BATCH CONFIGURATION
        self.BATCH_SIZE = 1000

    def process_approved_artifacts(self):
        artifacts = self.db.execute(
            select(DiscoveredArtifact)
            .where(DiscoveredArtifact.status == 'APPROVED')
            .order_by(DiscoveredArtifact.created_at.asc())
        ).scalars().all()

        logger.info(f"Found {len(artifacts)} APPROVED artifacts.")
        for artifact in artifacts:
            self._process_single_artifact(artifact)

    def _sanitize_course_name(self, raw_name: str) -> str:
        if not raw_name: return "UNKNOWN"
        name = raw_name.upper()
        
        patterns_to_remove = [
            r"\(HK\)", r"\bHK\b",
            r"\(AGRICULTURIST QUOTA\)", r"\bAGRICULTURIST QUOTA\b",
            r"\(PRIVATE\)", r"\bPRIVATE\b",
            r"\(NRI\)", r"\bNRI\b",
            r"\(SPECIAL\)", r"\bSPECIAL\b"
        ]
        
        for pattern in patterns_to_remove:
            name = re.sub(pattern, "", name)

        name = name.replace("&", "_").replace("-", "_")
        name = name.replace("(", "").replace(")", "")
        name = re.sub(r"[\s_]+", "_", name)
        
        return name.strip("_")

    def _process_single_artifact(self, artifact: DiscoveredArtifact):
        ingestion_run_id = uuid.uuid4()
        local_path = None
        logger.info(f"Starting Run {ingestion_run_id} for Artifact {artifact.id}")

        try:
            local_path = self._download_file(artifact.pdf_path, artifact.id)
            parser = KCETTableParser(local_path)
            sanitized_stream = self._sanitize_course_name(artifact.round_name)
            
            stats = {"committed": 0, "quarantined": 0}
            
            # BATCH BUFFERS
            outcome_buffer = []
            quarantine_buffer = []
            identity_buffer = []

            for row in parser.parse():
                # Resolve Context (Row-by-Row required for Identity/Taxonomy checks)
                self._handle_row(
                    row, artifact, ingestion_run_id, stats, sanitized_stream, 
                    outcome_buffer, quarantine_buffer, identity_buffer
                )
                
                # FLUSH BATCHES IF FULL
                if len(outcome_buffer) >= self.BATCH_SIZE:
                    self._flush_outcomes(outcome_buffer)
                if len(quarantine_buffer) >= self.BATCH_SIZE:
                    self._flush_quarantine(quarantine_buffer)
                if len(identity_buffer) >= self.BATCH_SIZE: 
                    self._flush_identity(identity_buffer) 

            # FLUSH REMAINING
            self._flush_outcomes(outcome_buffer)
            self._flush_quarantine(quarantine_buffer)
            self._flush_identity(identity_buffer)

            # Final Status Update
            self.db.execute(
                update(DiscoveredArtifact).where(DiscoveredArtifact.id == artifact.id)
                .values(status="INGESTED", review_notes=f"Run {ingestion_run_id}: {stats}")
            )
            self.db.commit()

        except Exception as e:
            logger.error(f"Run {ingestion_run_id} FAILED: {str(e)}")
            self.db.rollback()
            self.db.execute(
                update(DiscoveredArtifact).where(DiscoveredArtifact.id == artifact.id)
                .values(status="FAILED", review_notes=str(e))
            )
            self.db.commit()
        finally:
            if local_path and os.path.exists(local_path): os.remove(local_path)

    def _handle_row(self, row, artifact, run_id, stats, stream, outcome_buf, quarantine_buf, identity_buf):
        try:
            loc_norm = "GEN" if row['seat_type'] == "GENERAL" else "HK"
            if row['seat_type'] == "PRIVATE": loc_norm = "PVT"

            context_input = {
                "college_name_raw": row['college_name_raw'],
                "source_type": "kcet_pdf",
                "course_type_normalized": stream,
                "location_type_normalized": loc_norm,
                "category_raw": row['category_raw'],
                "year": artifact.year,
                "round": artifact.round_number,
                "kea_code": row['kea_code'],
                "course_code_raw": row['course_code_raw'],
                "course_name_raw": row['course_name_raw']
            }

            resolved = self.context_manager.resolve_context(
                db=self.db, adapter=self.adapter, row_data=context_input,
                mode=RegistryMode.BOOTSTRAP, ingestion_run_id=run_id
            )

            if not resolved:
                identity_buf.append({
                    "raw_name": row['college_name_raw'],
                    "source_document": str(artifact.id),
                    "reason_flagged": "Identity Resolution Failed",
                    "status": "pending",
                    "ingestion_run_id": run_id
                    # REMOVED created_at: The database handles this via server_default=func.now()
                })
                stats['quarantined'] += 1
                return

            # ADD TO BUFFER (Optimization: Don't insert yet)
            outcome_buf.append({
                "college_id": resolved.college_id,
                "exam_code": resolved.exam_code,
                "year": resolved.year,
                "round_number": resolved.round,
                "institute_code": resolved.institute_code,
                "institute_name": resolved.institute_name,
                "program_code": resolved.program_code,
                "program_name": resolved.program_name,
                "seat_bucket_code": resolved.seat_bucket_code,
                "closing_rank": int(float(row['cutoff_rank'])),
                "source_authority": resolved.exam_code,
                "created_by": "etl_system",
                "source_file": str(artifact.id),
                "ingestion_run_id": run_id,
                "is_latest": True
            })
            stats['committed'] += 1

        except PolicyViolationError as e:
            quarantine_buf.append({
                "exam_code": artifact.exam_code, "seat_bucket_code": "UNKNOWN",
                "violation_type": "POLICY_VIOLATION", "source_exam": "KCET",
                "source_year": artifact.year, "source_file": str(artifact.id),
                "raw_row": row, "ingestion_run_id": run_id, "review_notes": str(e)
            })
            stats['quarantined'] += 1
        except Exception as e:
            quarantine_buf.append({
                "exam_code": artifact.exam_code, "seat_bucket_code": "SYSTEM_ERROR",
                "violation_type": "CRASH", "source_exam": "KCET",
                "source_year": artifact.year, "source_file": str(artifact.id),
                "raw_row": row, "ingestion_run_id": run_id, "review_notes": str(e)
            })
            stats['quarantined'] += 1

    def _flush_outcomes(self, buffer):
        if not buffer: return
        self.db.execute(insert(CutoffOutcome), buffer)
        buffer.clear()

    def _flush_quarantine(self, buffer):
        if not buffer: return
        self.db.execute(insert(SeatPolicyQuarantine), buffer)
        buffer.clear()
    
    def _flush_identity(self, buffer):
        if not buffer: return
        # We use strict insert here
        self.db.execute(insert(CollegeCandidate), buffer)
        buffer.clear()

    def _download_file(self, url: str, artifact_id) -> str:
        local_filename = os.path.join(self.temp_dir, f"{artifact_id}.pdf")
        if url.startswith("http"):
            # AUDIT FIX: Verify SSL explicitly (True is default, but explicit is better)
            # If internal CA issues exist, map volume /etc/ssl/certs instead of verify=False
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            with open(local_filename, 'wb') as f: shutil.copyfileobj(response.raw, f)
        else:
            shutil.copy(url, local_filename)
        return local_filename

if __name__ == "__main__":
    db = SessionLocal()
    processor = ArtifactProcessor(db)
    processor.process_approved_artifacts()
    db.close()