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
    CollegeCandidate, ExamConfiguration, IngestionRun,
    ExamCourseTypeCandidate, ExamBranchCandidate
)
from app.services.registry_service import RegistryService, RegistryMode
from app.domains.admin_portal.services.janitor_service import JanitorService
from ingestion.common.services.context_manager import ContextManager, PolicyViolationError
from ingestion.common.services.plugin_factory import PluginFactory 
from ingestion.common.services.taxonomy_cache import TaxonomyCache
from ingestion.common.services.taxonomy_ingestion_service import TaxonomyIngestionEngine
from app.domains.student_portal.college_filter_tool.services.college_filter_rebuild_dispatcher import (
    CollegeFilterRebuildMode,
    CollegeFilterRebuildRequest,
    college_filter_rebuild_dispatcher,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Universal_Orchestrator")
MH_MEDICAL_EXAM_CODES = {"mh_neet_ug", "mh_ayush_aiq", "mh_nursing"}

class ArtifactProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.registry = RegistryService()
        self.context_manager = ContextManager(self.registry)
        
        self.temp_dir = "/src/temp_downloads"
        os.makedirs(self.temp_dir, exist_ok=True)
        self.BATCH_SIZE = 1000

    def process_approved_artifacts(
        self,
        specific_exam: str = None,
        skip_rebuild: bool = False,
    ):
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
            self._process_single_artifact(
                artifact,
                skip_rebuild=skip_rebuild,
            )

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

    def _process_single_artifact(
        self,
        artifact: DiscoveredArtifact,
        skip_rebuild: bool = False,
    ):
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
                self.db.execute(delete(CutoffOutcome).where(
                    CutoffOutcome.source_document == str(artifact.id)
                ))

                self.db.execute(delete(SeatPolicyQuarantine).where(
                    SeatPolicyQuarantine.source_file == str(artifact.id)
                ))
                
                self.db.execute(delete(CollegeCandidate).where(
                    CollegeCandidate.source_document == str(artifact.id)
                ))

                self.db.execute(delete(ExamCourseTypeCandidate).where(
                    and_(
                        ExamCourseTypeCandidate.source_artifact_id == artifact.id,
                        ExamCourseTypeCandidate.status == 'PENDING'
                    )
                ))

                self.db.execute(delete(ExamBranchCandidate).where(
                    and_(
                        ExamBranchCandidate.source_artifact_id == artifact.id,
                        ExamBranchCandidate.status == 'PENDING'
                    )
                ))

                self.db.flush()

           # 3. DOWNLOAD & PREPARE
            local_path = self._download_file(artifact.pdf_path, artifact.id, plugin)
            
            # --- DYNAMIC PARSER RESOLUTION ---
            if hasattr(plugin, 'get_parser_with_context'):
                parser = plugin.get_parser_with_context(local_path, artifact)
            else:
                parser = plugin.get_parser(local_path)
            
            adapter = plugin.get_adapter()
            sanitized_stream = plugin.sanitize_round_name(artifact.round_name)
            
            stats = {"committed": 0, "quarantined": 0}
            
            # 4. INITIALIZE BUFFERS
            outcome_buf = []
            quarantine_buf = []
            identity_buf = []

            taxonomy_cache = TaxonomyCache(self.db, artifact.exam_code)
            unknown_branches = set()
            unknown_courses = set()

            # 5. PARSING LOOP
            for row in parser.parse():
                self._handle_row(
                    row=row, artifact=artifact, run_id=ingestion_run_id, 
                    stats=stats, stream=sanitized_stream, mode=mode, 
                    outcome_buf=outcome_buf, quarantine_buf=quarantine_buf, 
                    identity_buf=identity_buf, adapter=adapter, plugin=plugin,
                    taxonomy_cache=taxonomy_cache,
                    unknown_branches=unknown_branches,
                    unknown_courses=unknown_courses
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

            # ========================================================
            # 7. POST-COMMIT COLLEGE-FILTER REBUILD DISPATCH
            # ========================================================
            try:
                if not skip_rebuild:
                    college_filter_rebuild_dispatcher.dispatch(
                        CollegeFilterRebuildRequest(
                            reason="POST_INGEST",
                            rebuild_mode=CollegeFilterRebuildMode.FULL_STACK,
                            trigger_exam_code=artifact.exam_code,
                            created_by="system:artifact_processor",
                        )
                    )
                else:
                    logger.info(
                        "Skipped college-filter rebuild dispatch for artifact %s "
                        "because skip_rebuild=True",
                        artifact.id,
                    )
            except Exception:
                logger.exception(
                    "Failed to dispatch college-filter rebuild after successful ingest "
                    "artifact_id=%s exam_code=%s run_id=%s",
                    artifact.id,
                    artifact.exam_code,
                    ingestion_run_id,
                )

            # ========================================================
            # 8. TAXONOMY AIRLOCK DISPATCH (Session Isolated, NON-FATAL)
            # ========================================================
            try:
                if unknown_branches or unknown_courses:
                    with SessionLocal() as taxonomy_db:
                        if unknown_branches:
                            logger.info(
                                "Dispatching %s unknown branches to Airlock.",
                                len(unknown_branches),
                            )
                            TaxonomyIngestionEngine.process_pdf_batch(
                                taxonomy_db,
                                artifact.exam_code,
                                list(unknown_branches),
                                artifact.id,
                                "branch",
                            )
                        if unknown_courses:
                            logger.info(
                                "Dispatching %s unknown courses to Airlock.",
                                len(unknown_courses),
                            )
                            TaxonomyIngestionEngine.process_pdf_batch(
                                taxonomy_db,
                                artifact.exam_code,
                                list(unknown_courses),
                                artifact.id,
                                "course_type",
                            )
            except Exception:
                logger.exception(
                    "Failed to dispatch taxonomy airlock after successful ingest "
                    "artifact_id=%s exam_code=%s run_id=%s",
                    artifact.id,
                    artifact.exam_code,
                    ingestion_run_id,
                )

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

    def _handle_row(self, row, artifact, run_id, stats, stream, mode, outcome_buf, quarantine_buf, identity_buf, adapter, plugin, taxonomy_cache, unknown_branches, unknown_courses):
        context_input = {}
        try:
            # 1. Enrich Data
            context_input = plugin.transform_row_to_context(row, artifact, stream)
            
            # [MH MEDICAL ONLY] Course-type discovery must not depend on college identity.
            # These documents derive a trustworthy course type from institute code, even when
            # identity is still unresolved. We only pre-dispatch COURSE taxonomy here, never branch.
            is_mh_medical_exam = str(artifact.exam_code or "").strip().lower() in MH_MEDICAL_EXAM_CODES

            if is_mh_medical_exam:
                pre_identity_course = TaxonomyIngestionEngine._normalize_string(
                    context_input.get("specific_course_type")
                )
                if pre_identity_course and not taxonomy_cache.is_course_known(pre_identity_course):
                    unknown_courses.add(pre_identity_course)

            # 2. Resolve Context (Identity + Policy Check)
            resolved = self.context_manager.resolve_context(
                db=self.db, adapter=adapter, row_data=context_input,
                mode=mode, ingestion_run_id=run_id
            )

            if not resolved:
                # [AUDIT FIX 1]: Bulletproof Dictionary Extraction
                raw_col_name = row.get('college_name_raw') or context_input.get('college_name') or "UNKNOWN_COLLEGE"
                
                identity_buf.append({
                    "raw_name": raw_col_name,
                    "source_document": str(artifact.id),
                    "reason_flagged": "Identity Resolution Failed",
                    "status": "pending",
                    "ingestion_run_id": run_id
                })
                stats['quarantined'] += 1
                return

            # ========================================================
            # [AUDIT FIX 3]: Defensive protection against missing branch names
            # ========================================================
            if not resolved.program_name or not str(resolved.program_name).strip():
                raise PolicyViolationError("Missing program/branch name after context resolution")

            if not resolved.course_type or not str(resolved.course_type).strip():
                raise PolicyViolationError("Missing course type after context resolution")

            # ========================================================
            # [NEW] TAXONOMY GATEKEEPER 
            # ========================================================
            norm_branch = TaxonomyIngestionEngine._normalize_string(resolved.program_name)
            norm_course = TaxonomyIngestionEngine._normalize_string(resolved.course_type)

            # MH medical student-allotment documents do not provide a trustworthy branch dimension.
            # We still keep program_name/program_code as descriptive fields for outcomes,
            # but we must not route them into the branch taxonomy airlock.
            skip_branch_taxonomy = str(artifact.exam_code or "").strip().lower() in MH_MEDICAL_EXAM_CODES

            is_taxonomy_valid = True

            if not skip_branch_taxonomy:
                if norm_branch and not taxonomy_cache.is_branch_known(norm_branch):
                    unknown_branches.add(norm_branch)
                    is_taxonomy_valid = False

            if norm_course and not taxonomy_cache.is_course_known(norm_course):
                unknown_courses.add(norm_course)
                is_taxonomy_valid = False
                
            if not is_taxonomy_valid:
                quarantine_buf.append({
                    "exam_code": artifact.exam_code, 
                    "seat_bucket_code": resolved.seat_bucket_code,
                    "violation_type": "UNKNOWN_TAXONOMY", 
                    "source_exam": artifact.exam_code,
                    "source_year": artifact.year, 
                    "source_file": str(artifact.id),
                    "raw_row": {
                        "error": "Branch or Course Type not found in Canonical Registry.",
                        "branch": resolved.program_name,
                        "course": resolved.course_type
                    }, 
                    "ingestion_run_id": run_id, 
                    "review_notes": "Awaiting Admin Taxonomy Triage"
                })
                stats['quarantined'] += 1
                return
            # ========================================================

            # --- [ENTERPRISE FIX]: Bulletproof Rank Extraction ---
            def _extract_rank(key: str) -> int | None:
                val = context_input.get(key)
                if val is None:
                    val = row.get(key)
                
                if val is None:
                    return None
                    
                if isinstance(val, int):
                    return val
                    
                clean_val = str(val).strip().upper().replace("P", "").replace(",", "")
                try:
                    return int(float(clean_val))
                except ValueError:
                    return None
            # -----------------------------------------------------

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
                "opening_rank": _extract_rank('opening_rank'),
                "closing_rank": _extract_rank('cutoff_rank'),
                "cutoff_percentile": row.get('cutoff_percentile'),
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
                "raw_row": {"error": str(e), "attributes": policy_attrs}, 
                "ingestion_run_id": run_id, 
                "review_notes": str(e)
            })
            stats['quarantined'] += 1

    def _flush_outcomes(self, buffer):
        if not buffer: return
        
        # [ENTERPRISE SHIELD] Observable In-Memory Deduplication
        unique_map = {}
        for row in buffer:
            unique_key = (
                row['exam_code'],
                row['year'],
                row['round_number'],
                row['institute_code'],
                row['program_code'],
                row['seat_bucket_code']
            )
            
            if unique_key not in unique_map:
                unique_map[unique_key] = row
            else:
                existing_row = unique_map[unique_key]
                if existing_row['closing_rank'] != row['closing_rank']:
                    logger.error(
                        f"🚨 DATA COLLISION: Conflicting ranks found for {unique_key}! "
                        f"Rank A: {existing_row['closing_rank']} | Rank B: {row['closing_rank']}. "
                        f"Action: Preserving first extracted occurrence."
                    )
                else:
                    logger.debug(f"♻️ Dropped exact PDF pagination duplicate for {unique_key}")

        deduped_buffer = list(unique_map.values())
        
        keys = [k for k in unique_map.keys()]

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

        self.db.execute(insert(CutoffOutcome), deduped_buffer)
        buffer.clear()

    def _flush_quarantine(self, buffer):
        if not buffer: return
        self.db.execute(insert(SeatPolicyQuarantine), buffer)
        buffer.clear()
    
    def _flush_identity(self, buffer):
        if not buffer: return
        self.db.execute(insert(CollegeCandidate), buffer)
        buffer.clear()

    def _download_file(self, url: str, artifact_id, plugin=None) -> str:
        from urllib.parse import urlparse, urljoin
        from bs4 import BeautifulSoup
        import os, requests, shutil, re, base64
        
        local_filename = os.path.join(self.temp_dir, f"{artifact_id}.pdf")
        if url.startswith("http"):
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            if plugin and hasattr(plugin, 'get_request_headers'):
                headers.update(plugin.get_request_headers())
            
            session = requests.Session()
            session.headers.update(headers)
            
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            session.headers.update({"Referer": base_url}) 
            
            logger.info(f"🔄 Bootstrapping Session from {base_url}...")
            try:
                session.get(base_url, timeout=15) 
            except Exception: pass

            logger.info(f"⬇️ Downloading artifact from {url}...")
            response = session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            raw_content = response.content
            content_type = response.headers.get('Content-Type', '').lower()
            
            if raw_content.startswith(b'%PDF'):
                logger.info("✅ Raw PDF bytes detected. Bypassing Content-Type header lie.")
                with open(local_filename, 'wb') as f: 
                    f.write(raw_content)
                return local_filename
            
            if 'text/html' in content_type or not raw_content.startswith(b'%PDF'):
                logger.info(f"📄 Detected HTML response. Searching for hidden PDF payloads...")
                
                b64_match = re.search(r'[\'"](JVBER[A-Za-z0-9+/=]+)[\'"]', response.text)
                if b64_match:
                    logger.info("🧩 Found Base64 encoded PDF payload inside JavaScript! Decoding...")
                    pdf_bytes = base64.b64decode(b64_match.group(1))
                    with open(local_filename, 'wb') as f:
                        f.write(pdf_bytes)
                    return local_filename

                soup = BeautifulSoup(raw_content, 'html.parser')
                pdf_url = None
                
                iframe = soup.find('iframe')
                if iframe and iframe.get('src'):
                    pdf_url = iframe.get('src')
                elif soup.find('object', type='application/pdf'):
                    pdf_url = soup.find('object', type='application/pdf').get('data')
                elif soup.find('embed', type='application/pdf'):
                    pdf_url = soup.find('embed', type='application/pdf').get('src')
                elif soup.find('a', href=lambda h: h and '.pdf' in h.lower()):
                    pdf_url = soup.find('a', href=lambda h: h and '.pdf' in h.lower()).get('href')
                else:
                    match = re.search(r'[\'"]([^\'"]+\.pdf)[\'"]', response.text, re.IGNORECASE)
                    if match: pdf_url = match.group(1)

                if not pdf_url:
                    logger.error(f"❌ HTML DUMP (First 1000 chars):\n{response.text[:1000]}\n")
                    raise ValueError("Blocked by Server. No PDF found. (See HTML Dump in logs above).")
                
                pdf_url = urljoin(url, pdf_url)
                logger.info(f"🔗 Resolved True PDF URL: {pdf_url}")
                
                response = session.get(pdf_url, stream=True, timeout=30)
                response.raise_for_status()
                
                if not response.content.startswith(b'%PDF'):
                    raise ValueError("Extracted URL still did not return raw PDF bytes.")
                    
                with open(local_filename, 'wb') as f: 
                    f.write(response.content)

        else:
            shutil.copy(url, local_filename)
            
        return local_filename

if __name__ == "__main__":
    db = SessionLocal()
    processor = ArtifactProcessor(db)
    processor.process_approved_artifacts()
    db.close()