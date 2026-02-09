import os
import uuid
import logging
import requests
import shutil
from sqlalchemy import select, update, insert, delete, or_, and_, tuple_
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import traceback

from app.database import SessionLocal
from app.models import (
    DiscoveredArtifact, CutoffOutcome, SeatPolicyQuarantine, 
    CollegeCandidate, ExamConfiguration, IngestionRun
)
from app.services.registry_service import RegistryService, RegistryMode
from app.domains.admin_portal.services.janitor_service import JanitorService
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
        Fetches APPROVED artifacts OR those marked for reprocessing.
        """
        query = select(DiscoveredArtifact).where(
            or_(
                DiscoveredArtifact.status == 'APPROVED',
                DiscoveredArtifact.requires_reprocessing == True
            )
        )
        
        if specific_exam:
            query = query.where(DiscoveredArtifact.exam_code == specific_exam)
            
        artifacts = self.db.execute(query.order_by(DiscoveredArtifact.created_at.asc())).scalars().all()

        logger.info(f"Found {len(artifacts)} artifacts to process.")
        for artifact in artifacts:
            self._process_single_artifact(artifact)

    def _get_ingestion_mode(self, exam_code: str) -> RegistryMode:
        try:
            config = self.db.execute(
                select(ExamConfiguration).where(ExamConfiguration.exam_code == exam_code)
            ).scalar_one_or_none()

            if not config or not config.ingestion_mode:
                logger.warning(f"No config for {exam_code}. Defaulting to CONTINUOUS.")
                return RegistryMode.CONTINUOUS 
            
            return RegistryMode(config.ingestion_mode)
        except Exception:
            return RegistryMode.CONTINUOUS

    def _process_single_artifact(self, artifact: DiscoveredArtifact):
        ingestion_run_id = uuid.uuid4()
        local_path = None
        
        try:
            self.db.execute(
                insert(IngestionRun).values(
                    run_id=ingestion_run_id,
                    artifact_id=artifact.id,
                    exam_code=artifact.exam_code,
                    status="RUNNING",
                    stats={}
                )
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to initialize IngestionRun: {e}")
            return

        try:
            # 1. LOAD PLUGIN & CONFIG
            plugin = PluginFactory.get_plugin(artifact.exam_code)
            mode = self._get_ingestion_mode(artifact.exam_code)
            
            logger.info(f"Starting Run {ingestion_run_id} | Exam: {artifact.exam_code} | Mode: {mode}")

            # 2. CONDITIONAL WIPING
            if mode == RegistryMode.BOOTSTRAP:
                logger.warning(f"🧹 BOOTSTRAP MODE: Wiping data for artifact {artifact.id}")
                JanitorService.wipe_artifact(self.db, artifact.id, artifact.exam_code)
            else:
                # [REFINED] CONTINUOUS MODE VERSIONING PREP
                logger.info(f"📎 CONTINUOUS MODE: Preparing versioning for {artifact.id}")
                
                # 1. Clear previous attempts by THIS SPECIFIC ARTIFACT ONLY.
                # This ensures idempotency if you re-run the same file multiple times.
                self.db.execute(delete(CutoffOutcome).where(
                    CutoffOutcome.source_document == str(artifact.id)
                ))

                self.db.execute(delete(SeatPolicyQuarantine).where(
                    SeatPolicyQuarantine.source_file == str(artifact.id)
                ))
                
                self.db.execute(delete(CollegeCandidate).where(
                    CollegeCandidate.source_document == str(artifact.id)
                ))
                self.db.flush()

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
                    row=row, artifact=artifact, run_id=ingestion_run_id, 
                    stats=stats, stream=sanitized_stream, mode=mode, 
                    outcome_buf=outcome_buf, quarantine_buf=quarantine_buf, 
                    identity_buf=identity_buf, adapter=adapter, plugin=plugin
                )
                
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
                    requires_reprocessing=False
                )
            )
            
            self.db.execute(
                update(IngestionRun)
                .where(IngestionRun.run_id == ingestion_run_id)
                .values(status="COMPLETED", stats=stats, completed_at=func.now())
            )
            self.db.commit()

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Run {ingestion_run_id} FAILED: {error_msg}")
            logger.error(traceback.format_exc())
            
            self.db.rollback()
            
            self.db.execute(
                update(DiscoveredArtifact).where(DiscoveredArtifact.id == artifact.id)
                .values(status="FAILED", review_notes=error_msg[:1000])
            )
            
            self.db.execute(
                update(IngestionRun)
                .where(IngestionRun.run_id == ingestion_run_id)
                .values(status="FAILED", stats={"error": error_msg}, completed_at=func.now())
            )
            self.db.commit()
            
        finally:
            if local_path and os.path.exists(local_path): os.remove(local_path)

    def _handle_row(self, row, artifact, run_id, stats, stream, mode, outcome_buf, quarantine_buf, identity_buf, adapter, plugin):
        context_input = {}
        try:
            # 1. Enrich Data
            context_input = plugin.transform_row_to_context(row, artifact, stream)
            
            # 2. Resolve Context (Identity + Policy Check)
            resolved = self.context_manager.resolve_context(
                db=self.db, adapter=adapter, row_data=context_input,
                mode=mode, ingestion_run_id=run_id
            )

            if not resolved:
                # Identity Failure Case
                identity_buf.append({
                    "raw_name": row['college_name_raw'],
                    "source_document": str(artifact.id),
                    "reason_flagged": "Identity Resolution Failed",
                    "status": "pending",
                    "ingestion_run_id": run_id
                })
                stats['quarantined'] += 1
                return

            # 3. Success -> Add to Outcome Buffer
            outcome_buf.append({
                "college_id": resolved.college_id,
                "exam_code": resolved.exam_code,
                "year": resolved.year,
                "round_number": resolved.round,
                "state_code": resolved.state_code,
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
            try:
                real_slug = adapter.generate_slug(context_input)
                # Resolve the policy attributes using the ENRICHED context
                policy_attrs = adapter.resolve_policy_attributes(context_input)
            except Exception:
                real_slug = "UNKNOWN_ERROR"
                policy_attrs = {}

            quarantine_buf.append({
                "exam_code": artifact.exam_code, 
                "seat_bucket_code": real_slug,
                "violation_type": "POLICY_VIOLATION", 
                "source_exam": artifact.exam_code,
                "source_year": artifact.year, 
                "source_file": str(artifact.id),
                # CRITICAL: We save the policy_attrs here so the Triage Service 
                # can promote it without needing the original PDF or college info.
                "raw_row": policy_attrs, 
                "ingestion_run_id": run_id, 
                "review_notes": str(e)
            })
            stats['quarantined'] += 1

    def _flush_outcomes(self, buffer):
        if not buffer: return
        
        # 1. Collect unique composite keys for the batch update
        # These keys identify the specific seat categories across all colleges
        keys = [
            (
                row['exam_code'],
                row['year'],
                row['round_number'],
                row['institute_code'],
                row['program_code'],
                row['seat_bucket_code']
            )
            for row in buffer
        ]

        # 2. Set is_latest=False for all matching existing records in ONE statement
        # This satisfies the 'uq_cutoff_latest_only' constraint before the new insert
        self.db.execute(
            update(CutoffOutcome)
            .where(
                and_(
                    tuple_(
                        CutoffOutcome.exam_code,
                        CutoffOutcome.year,
                        CutoffOutcome.round_number,
                        CutoffOutcome.institute_code,
                        CutoffOutcome.program_code,
                        CutoffOutcome.seat_bucket_code
                    ).in_(keys),
                    CutoffOutcome.is_latest == True
                )
            )
            .values(is_latest=False)
        )

        # 3. Bulk insert the new batch as the new current 'latest' records
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