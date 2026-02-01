import os
import uuid
import logging
import requests
import shutil
from sqlalchemy import select, update, insert, delete
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    DiscoveredArtifact, CutoffOutcome, SeatPolicyQuarantine, 
    CollegeCandidate #, ExamConfiguration
)
from app.services.registry_service import RegistryService, RegistryMode
from ingestion.common.services.context_manager import ContextManager, PolicyViolationError
from ingestion.common.services.plugin_factory import PluginFactory 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Universal_Orchestrator")

class ArtifactProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.registry = RegistryService()
        self.context_manager = ContextManager(self.registry)
        
        self.temp_dir = "./temp_downloads"
        os.makedirs(self.temp_dir, exist_ok=True)
        self.BATCH_SIZE = 1000

    def process_approved_artifacts(self, specific_exam: str = None):
        """
        Fetches APPROVED artifacts. Optionally filters by exam code.
        """
        query = select(DiscoveredArtifact).where(DiscoveredArtifact.status == 'APPROVED')
        
        if specific_exam:
            query = query.where(DiscoveredArtifact.exam_code == specific_exam)
            
        artifacts = self.db.execute(query.order_by(DiscoveredArtifact.created_at.asc())).scalars().all()

        logger.info(f"Found {len(artifacts)} APPROVED artifacts.")
        for artifact in artifacts:
            self._process_single_artifact(artifact)

    def _get_ingestion_mode(self, exam_code: str) -> RegistryMode:
        """
        Dynamically fetches mode (BOOTSTRAP/CONTINUOUS) from DB.
        Defaults to BOOTSTRAP if config is missing.
        """
        try:
            config = self.db.execute(
                select(ExamConfiguration).where(ExamConfiguration.exam_code == exam_code)
            ).scalar_one_or_none()

            if not config or not config.ingestion_mode:
                return RegistryMode.BOOTSTRAP
            
            return RegistryMode(config.ingestion_mode)
        except Exception:
            logger.warning(f"Config check failed for {exam_code}. Defaulting to BOOTSTRAP.")
            return RegistryMode.BOOTSTRAP

    def _smart_wipe(self, artifact: DiscoveredArtifact, mode: RegistryMode):
        """
        Pre-Clean Logic:
        - BOOTSTRAP: Hard delete previous attempts for this file.
        - CONTINUOUS: Soft delete (retire) previous rows.
        """
        if mode == RegistryMode.BOOTSTRAP:
            logger.info(f"Performing BOOTSTRAP Hard Delete for Artifact {artifact.id}")
            self.db.execute(
                delete(CutoffOutcome).where(CutoffOutcome.source_document == str(artifact.id))
            )
        else:
            logger.info(f"Performing CONTINUOUS Soft Delete for Artifact {artifact.id}")
            self.db.execute(
                update(CutoffOutcome)
                .where(CutoffOutcome.source_document == str(artifact.id))
                .values(is_latest=False)
            )
        self.db.commit()

    def _process_single_artifact(self, artifact: DiscoveredArtifact):
        ingestion_run_id = uuid.uuid4()
        local_path = None
        
        try:
            # 1. LOAD PLUGIN & CONFIG
            plugin = PluginFactory.get_plugin(artifact.exam_code)
            mode = self._get_ingestion_mode(artifact.exam_code)
            
            logger.info(f"Starting Run {ingestion_run_id} | Exam: {artifact.exam_code} | Mode: {mode}")

            # 2. SMART WIPE
            self._smart_wipe(artifact, mode)

            # 3. DOWNLOAD & PREPARE
            local_path = self._download_file(artifact.pdf_path, artifact.id)
            parser = plugin.get_parser(local_path)
            adapter = plugin.get_adapter()
            sanitized_stream = plugin.sanitize_round_name(artifact.round_name)
            
            stats = {"committed": 0, "quarantined": 0}
            
            # 4. INITIALIZE BUFFERS
            outcome_buf = []
            quarantine_buf = []
            identity_buf = []

            # 5. PARSING LOOP
            for row in parser.parse():
                self._handle_row(
                    row=row, 
                    artifact=artifact, 
                    run_id=ingestion_run_id, 
                    stats=stats, 
                    stream=sanitized_stream, 
                    mode=mode, 
                    outcome_buf=outcome_buf, 
                    quarantine_buf=quarantine_buf, 
                    identity_buf=identity_buf,
                    adapter=adapter, 
                    plugin=plugin
                )
                
                # Flush logic
                if len(outcome_buf) >= self.BATCH_SIZE: self._flush_outcomes(outcome_buf)
                if len(quarantine_buf) >= self.BATCH_SIZE: self._flush_quarantine(quarantine_buf)
                if len(identity_buf) >= self.BATCH_SIZE: self._flush_identity(identity_buf) 

            # Flush Remaining
            self._flush_outcomes(outcome_buf)
            self._flush_quarantine(quarantine_buf)
            self._flush_identity(identity_buf)

            # 6. SUCCESS STATE
            self.db.execute(
                update(DiscoveredArtifact).where(DiscoveredArtifact.id == artifact.id)
                .values(
                    status="INGESTED", 
                    review_notes=f"Run {ingestion_run_id}: {stats}",
                    requires_reprocessing=False  # Clear dirty flag
                )
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

    def _handle_row(self, row, artifact, run_id, stats, stream, mode, outcome_buf, quarantine_buf, identity_buf, adapter, plugin):
        try:
            # Delegate context creation to plugin
            context_input = plugin.transform_row_to_context(row, artifact, stream)

            # Resolve using Dynamic Mode
            resolved = self.context_manager.resolve_context(
                db=self.db, adapter=adapter, row_data=context_input,
                mode=mode, ingestion_run_id=run_id
            )

            if not resolved:
                identity_buf.append({
                    "raw_name": row['college_name_raw'],
                    "source_document": str(artifact.id),
                    "reason_flagged": "Identity Resolution Failed",
                    "status": "pending",
                    "ingestion_run_id": run_id
                })
                stats['quarantined'] += 1
                return

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
                "created_by": "universal_etl",
                "source_document": str(artifact.id),
                "ingestion_run_id": run_id,
                "is_latest": True
            })
            stats['committed'] += 1

        except PolicyViolationError as e:
            quarantine_buf.append({
                "exam_code": artifact.exam_code, "seat_bucket_code": "UNKNOWN",
                "violation_type": "POLICY_VIOLATION", "source_exam": artifact.exam_code,
                "source_year": artifact.year, "source_document": str(artifact.id),
                "raw_row": row, "ingestion_run_id": run_id, "review_notes": str(e)
            })
            stats['quarantined'] += 1
        except Exception as e:
            quarantine_buf.append({
                "exam_code": artifact.exam_code, "seat_bucket_code": "SYSTEM_ERROR",
                "violation_type": "CRASH", "source_exam": artifact.exam_code,
                "source_year": artifact.year, "source_document": str(artifact.id),
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
        self.db.execute(insert(CollegeCandidate), buffer)
        buffer.clear()

    def _download_file(self, url: str, artifact_id) -> str:
        local_filename = os.path.join(self.temp_dir, f"{artifact_id}.pdf")
        if url.startswith("http"):
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