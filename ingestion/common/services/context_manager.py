from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from typing import Dict, Any, Optional
import uuid

from app.models import SeatBucketTaxonomy
from app.services.registry_service import RegistryService, RegistryMode
from ingestion.common.interface.context_interface import ContextAdapter, ResolvedContext

class PolicyViolationError(Exception):
    """
    Raised when a new seat bucket is detected in Continuous Mode.
    The Engine MUST catch this, ROLLBACK, and log to 'seat_policy_quarantine'.
    """
    pass

class ContextManager:
    """
    The Universal Gatekeeper.
    Passive Unit of Work: Prepares state, validates policy, flushes data.
    Does NOT Commit.
    """
    def __init__(self, registry_service: RegistryService):
        self.registry = registry_service

    def resolve_context(
        self,
        db: Session,
        adapter: ContextAdapter,
        row_data: Dict[str, Any],
        mode: RegistryMode,
        ingestion_run_id: uuid.UUID
    ) -> Optional[ResolvedContext]:
        
        # 1. Identity
        identity_result = self.registry.resolve_identity(
            db, 
            raw_name=row_data['college_name_raw'], 
            source_type=row_data.get('source_type', 'unknown'),
            mode=mode,
            ingestion_run_id=ingestion_run_id
        )
        if not identity_result.college_id: return None 

        # 2. Validation & Policy (Fail Fast)
        try:
            # Validate Round FIRST. If invalid, we quarantine immediately.
            valid_round = adapter.resolve_round(row_data) 
            slug = adapter.generate_slug(row_data)
            
            # [CRITICAL FIX] Moved policy attributes resolution INTO the safety block.
            # If the Adapter throws a ValueError (e.g. Unrecognized Category 'D'),
            # it is safely caught and converted into a Quarantine Event.
            policy_attrs = adapter.resolve_policy_attributes(row_data)
            
        except ValueError as e:
             raise PolicyViolationError(str(e)) # Convert to Quarantine Event

        # 3. Governance
        self._ensure_taxonomy(db, slug, adapter.get_exam_code(), policy_attrs, mode)

        # 4. Metadata
        adapter.upsert_exam_metadata(db, identity_result.college_id, row_data)

        # 5. Descriptive
        desc = adapter.resolve_descriptive_attributes(row_data)

        return ResolvedContext(
            college_id=identity_result.college_id,
            seat_bucket_code=slug,
            exam_code=adapter.get_exam_code(),
            year=row_data['year'],
            round=valid_round, 
            state_code=adapter.get_state_code(row_data),
            
            course_type=policy_attrs.get('course_type'),
            location_type=policy_attrs.get('location_type'),
            reservation_type=policy_attrs.get('reservation_type'),

            institute_code=desc['institute_code'],
            institute_name=desc['institute_name'],
            program_code=desc['program_code'],
            program_name=desc['program_name']
        )

    def _ensure_taxonomy(
        self, 
        db: Session, 
        slug: str, 
        exam_code: str, 
        attrs: Dict[str, Any], 
        mode: RegistryMode
    ):
        exists = db.execute(
            select(SeatBucketTaxonomy.seat_bucket_code)
            .where(SeatBucketTaxonomy.seat_bucket_code == slug)
        ).scalar()

        if exists:
            return 

        if mode != RegistryMode.BOOTSTRAP:
            raise PolicyViolationError(f"Bucket '{slug}' unknown in Continuous Mode.")

        stmt = insert(SeatBucketTaxonomy).values(
            seat_bucket_code=slug,
            exam_code=exam_code,
            category_name=attrs['category_group'], 
            is_reserved=attrs['is_reserved'],
            course_type=attrs.get('course_type'),
            location_type=attrs.get('location_type'),
            reservation_type=attrs.get('reservation_type'),
            attributes=attrs.get('extra_attributes', {})
        )
        db.execute(stmt)
        db.flush() # Stage the taxonomy entry