import re
import uuid
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text, select, func

logger = logging.getLogger(__name__)

class TaxonomyIngestionEngine:
    """
    Idempotent, highly-concurrent ingestion engine for Course and Branch strings.
    Designed to safely funnel raw PDF text into the Candidate Airlock queues.
    """
    MAX_STRING_LENGTH = 255

    @staticmethod
    def _normalize_string(val: str) -> str:
        """Matches DB Determinism Guard exact syntax."""
        if not val or not val.strip():
            return ""
            
        # 1. Truncate extreme PDF parser hallucinations to protect index performance
        if len(val) > TaxonomyIngestionEngine.MAX_STRING_LENGTH:
            val = val[:TaxonomyIngestionEngine.MAX_STRING_LENGTH]
            
        # 2. POSIX-compliant whitespace normalization and lowercase
        return re.sub(r'\s+', ' ', val.strip()).lower()

    @staticmethod
    def ingest_course_type(db: Session, exam_code: str, raw_name: str, artifact_id: uuid.UUID) -> bool:
        """
        Pushes a raw course type string into the candidate airlock.
        Returns True if a NEW candidate was inserted.
        """
        norm_name = TaxonomyIngestionEngine._normalize_string(raw_name)
        if not norm_name:
            return False

        # 1. Acquire the 64-bit Distributed Mutex
        db.execute(
            select(func.pg_advisory_xact_lock(
                func.hashtext(exam_code), 
                func.hashtext(norm_name)
            ))
        )

        # 2. Deterministic Cross-Table Ingestion Query
        stmt = text("""
            INSERT INTO exam_course_type_candidates 
                (exam_code, raw_name, normalized_name, status, source_artifact_id)
            SELECT 
                :exam_code, :raw_name, :norm_name, 'PENDING', :artifact_id
            WHERE NOT EXISTS (
                SELECT 1 FROM exam_course_types 
                WHERE exam_code = :exam_code AND normalized_name = :norm_name
            )
            AND NOT EXISTS (
                SELECT 1 FROM exam_course_type_aliases 
                WHERE exam_code = :exam_code AND normalized_alias = :norm_name
            )
            ON CONFLICT (exam_code, normalized_name) DO NOTHING
            RETURNING id;
        """)

        result = db.execute(stmt, {
            "exam_code": exam_code,
            "raw_name": raw_name[:TaxonomyIngestionEngine.MAX_STRING_LENGTH], 
            "norm_name": norm_name,
            "artifact_id": str(artifact_id)
        })
        
        return result.fetchone() is not None


    @staticmethod
    def ingest_branch(db: Session, exam_code: str, raw_name: str, artifact_id: uuid.UUID) -> bool:
        """
        Pushes a raw branch string into the candidate airlock.
        Returns True if a NEW candidate was inserted.
        """
        norm_name = TaxonomyIngestionEngine._normalize_string(raw_name)
        if not norm_name:
            return False

        # 1. Acquire the 64-bit Distributed Mutex
        db.execute(
            select(func.pg_advisory_xact_lock(
                func.hashtext(exam_code), 
                func.hashtext(norm_name)
            ))
        )

        # 2. Deterministic Cross-Table Ingestion Query
        stmt = text("""
            INSERT INTO exam_branch_candidates 
                (exam_code, raw_name, normalized_name, status, source_artifact_id)
            SELECT 
                :exam_code, :raw_name, :norm_name, 'PENDING', :artifact_id
            WHERE NOT EXISTS (
                SELECT 1 FROM exam_branch_registry 
                WHERE exam_code = :exam_code AND normalized_name = :norm_name
            )
            AND NOT EXISTS (
                SELECT 1 FROM exam_branch_aliases 
                WHERE exam_code = :exam_code AND normalized_alias = :norm_name
            )
            ON CONFLICT (exam_code, normalized_name) DO NOTHING
            RETURNING id;
        """)

        result = db.execute(stmt, {
            "exam_code": exam_code,
            "raw_name": raw_name[:TaxonomyIngestionEngine.MAX_STRING_LENGTH],
            "norm_name": norm_name,
            "artifact_id": str(artifact_id)
        })
        
        return result.fetchone() is not None

    @staticmethod
    def process_pdf_batch(db: Session, exam_code: str, extracted_strings: list[str], artifact_id: uuid.UUID, entity_type: str = "branch", batch_size: int = 50) -> int:
        """
        Highly efficient batch processor for Celery tasks.
        Releases advisory locks periodically to prevent Postgres memory exhaustion.
        """
        new_discoveries = 0
        counter = 0
        
        # Ensure we start with a clean transaction boundary
        if not db.in_transaction():
            db.begin()

        try:
            for raw_string in extracted_strings:
                if entity_type == "branch":
                    is_new = TaxonomyIngestionEngine.ingest_branch(db, exam_code, raw_string, artifact_id)
                elif entity_type == "course_type":
                    is_new = TaxonomyIngestionEngine.ingest_course_type(db, exam_code, raw_string, artifact_id)
                else:
                    raise ValueError(f"Unknown entity type: {entity_type}")

                if is_new:
                    new_discoveries += 1
                    logger.info(f"🆕 Queued new {entity_type} candidate: '{raw_string}'")
                
                counter += 1
                
                # Release locks and establish new transaction boundary
                if counter % batch_size == 0:
                    db.commit()
                    db.begin()
                    
            # Final commit for the remaining items in the last batch
            db.commit()
            return new_discoveries
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Taxonomy Ingestion Batch Failed: {str(e)}")
            raise e