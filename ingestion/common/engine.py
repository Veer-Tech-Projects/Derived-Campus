import uuid
import logging
from typing import Dict, Any, Literal
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import update, and_  # Added for SCD Type 2

from app.models import (
    CutoffOutcome, 
    CollegeCandidate, 
    SeatPolicyQuarantine
)
from app.services.registry_service import RegistryMode
from ingestion.common.services.context_manager import ContextManager, PolicyViolationError
from ingestion.common.interface.context_interface import ContextAdapter, ResolvedContext

logger = logging.getLogger(__name__)

class UniversalIngestionEngine:
    """
    The Core Processing Unit for Cutoff Data.
    Implements:
    1. Identity Resolution (via Registry)
    2. Policy Enforcement (via ContextManager)
    3. SCD Type 2 Storage (Retire Old -> Insert New)
    """
    
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager

    def process_row(
        self, 
        db: Session, 
        row: Dict[str, Any], 
        adapter: ContextAdapter, 
        mode: RegistryMode, 
        ingestion_run_id: uuid.UUID
    ) -> Literal["ACCEPTED", "QUARANTINED_IDENTITY", "QUARANTINED_POLICY", "FAILED"]:
        try:
            # 1. Resolve Context (Identity & Policy)
            context = self.context_manager.resolve_context(
                db, adapter, row, mode, ingestion_run_id
            )

            # 2. Check Identity Quarantine
            if not context:
                db.rollback() 
                self._log_identity_quarantine(db, row, ingestion_run_id)
                return "QUARANTINED_IDENTITY"

            # 3. Write Fact (SCD Type 2)
            self._write_cutoff_fact(db, context, row, ingestion_run_id)

            db.commit()
            return "ACCEPTED"

        except PolicyViolationError as e:
            db.rollback()
            self._log_policy_quarantine(db, row, adapter, str(e), ingestion_run_id)
            return "QUARANTINED_POLICY"

        except Exception as e:
            db.rollback()
            logger.error(f"Row processing failed: {str(e)}", exc_info=True)
            return "FAILED"

    def _write_cutoff_fact(
        self, 
        db: Session, 
        context: ResolvedContext, 
        row: Dict[str, Any], 
        run_id: uuid.UUID
    ):
        """
        Writes the Cutoff Fact using SCD Type 2 Logic.
        1. Retires any existing 'Latest' record for this specific bucket.
        2. Inserts the new record as 'Latest'.
        """
        
        # --- Step A: Validation ---
        try:
            # Handle string ranks like "12,345" or "45.5"
            closing_rank_str = str(row.get('cutoff_rank', 0)).replace(',', '')
            closing_rank = int(float(closing_rank_str)) # Float cast handles 2025 decimals safely
            if closing_rank <= 0: raise ValueError("Positive rank required")
        except (ValueError, TypeError):
            raise ValueError(f"Invalid rank: {row.get('cutoff_rank')}")
        
        opening_rank = None
        if 'opening_rank' in row:
            try: 
                op_str = str(row['opening_rank']).replace(',', '')
                opening_rank = int(float(op_str))
            except: pass

        # --- Step B: SCD Type 2 Retirement (The "Soft Delete") ---
        # Before inserting, we must mark the PREVIOUS active record as inactive.
        # This prevents duplicate "Active" cutoffs for the same college/round/category.
        stmt = (
            update(CutoffOutcome)
            .where(
                and_(
                    CutoffOutcome.exam_code == context.exam_code,
                    CutoffOutcome.year == context.year,
                    CutoffOutcome.round_number == context.round,
                    CutoffOutcome.institute_code == context.institute_code,
                    CutoffOutcome.program_code == context.program_code,
                    CutoffOutcome.seat_bucket_code == context.seat_bucket_code,
                    CutoffOutcome.is_latest == True  # Only target the current active row
                )
            )
            .values(is_latest=False) # Retire it
        )
        db.execute(stmt)

        # --- Step C: Insert New Fact (Active) ---
        fact = CutoffOutcome(
            # Linkage
            college_id=context.college_id,
            seat_bucket_code=context.seat_bucket_code,
            
            # Dimensions (From Context)
            exam_code=context.exam_code,
            state_code=context.state_code, 
            year=context.year,
            round_number=context.round, 
            
            # Descriptive (From Context - UNIVERSAL)
            institute_code=context.institute_code,
            institute_name=context.institute_name,
            program_code=context.program_code,
            program_name=context.program_name,
            
            # Metrics
            opening_rank=opening_rank,
            closing_rank=closing_rank,
            
            # Audit
            source_authority=context.exam_code,
            source_document=row.get('source_document', 'unknown'),
            ingestion_run_id=run_id,
            created_by="universal_engine",
            
            # SCD Flag
            is_latest=True 
        )
        db.add(fact)
        db.flush()

    def _log_identity_quarantine(self, db: Session, row: Dict, run_id: uuid.UUID):
        try:
            stmt = insert(CollegeCandidate).values(
                raw_name=row.get('college_name_raw', 'UNKNOWN'),
                source_document=row.get('source_document', 'unknown'),
                reason_flagged="Identity Resolution Failed",
                status="pending",
                ingestion_run_id=run_id
            )
            db.execute(stmt)
            db.commit()
        except:
            db.rollback()

    def _log_policy_quarantine(self, db: Session, row: Dict, adapter: ContextAdapter, reason: str, run_id: uuid.UUID):
        try:
            try: slug = adapter.generate_slug(row)
            except: slug = "UNKNOWN"

            stmt = insert(SeatPolicyQuarantine).values(
                exam_code=adapter.get_exam_code(),
                seat_bucket_code=slug,
                violation_type="POLICY_VIOLATION",
                source_exam=adapter.get_exam_code(),
                source_year=row.get('year', 0),
                source_round=row.get('round'),
                source_file=row.get('source_document'),
                raw_row=row,
                status="OPEN",
                ingestion_run_id=run_id
            )
            db.execute(stmt)
            db.commit()
        except:
            db.rollback()