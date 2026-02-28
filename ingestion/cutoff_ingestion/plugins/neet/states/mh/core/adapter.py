from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
import logging

from app.models import MhtcetCollegeMetadata 
from ingestion.common.interface.context_interface import ContextAdapter
from ingestion.cutoff_ingestion.plugins.neet.states.mh.core.row_standardizer import MHNeetRowStandardizer

logger = logging.getLogger(__name__)

class MHNeetContextAdapter(ContextAdapter):
    
    def __init__(self, exam_slug: str):
        self.exam_slug = exam_slug
        
    def get_exam_code(self) -> str:
        return self.exam_slug.upper()

    def get_state_code(self, row: Dict[str, Any]) -> Optional[str]:
        # DATA-DRIVEN AIQ DETECTION
        if row.get('quota_normalized') == "AIQ": 
            return "AI"
        return "MH"

    def resolve_round(self, row: Dict[str, Any]) -> int:
        try:
            r = int(row.get('round'))
            if r < 1: raise ValueError
            return r
        except (TypeError, ValueError):
            raise ValueError(f"Invalid or missing round for MH NEET: {row.get('round')}")

    def generate_slug(self, row: Dict[str, Any]) -> str:
        # Values are already cleanly normalized by the parser BEFORE aggregation!
        dims = {
            "quota": row.get('quota_normalized', 'STATE'),
            "category": row.get('category_normalized', 'OPEN'),
            "gender": row.get('gender_normalized', 'General')
        }
        return MHNeetRowStandardizer.build_seat_bucket(row['exam_code'], dims)

    def resolve_policy_attributes(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "is_reserved": MHNeetRowStandardizer.is_reserved(row.get('category_normalized', '')),
            "category_group": row.get('category_normalized', 'OPEN'),
            "course_type": row['exam_code'],
            "location_type": row.get('quota_normalized', 'STATE'),
            "reservation_type": row.get('gender_normalized', 'General'),
            "extra_attributes": {
                "normalized_quota": row.get('quota_normalized')
            }
        }

    def resolve_descriptive_attributes(self, row: Dict[str, Any]) -> Dict[str, str]:
        # [ENTERPRISE FIX]: Uses the newly injected 'program_code', defaults to exam_code if missing
        prog_code = str(row.get('program_code')) if row.get('program_code') and row.get('program_code') != 'UNKNOWN_COURSE' else str(row.get('exam_code', 'UNKNOWN'))
        
        return {
            "institute_code": str(row.get('institute_code', 'UNKNOWN')),
            "institute_name": str(row.get('institute_name', 'UNKNOWN')),
            "program_code": prog_code,
            "program_name": prog_code.replace('_', ' ') # E.g., "MBBS_BDS" -> "MBBS BDS"
        }

    def upsert_exam_metadata(self, db: Session, college_id: UUID, row: Dict[str, Any]):
        # [ENTERPRISE FIX]: Defensively clean empty strings to None for strict PostgreSQL UUID columns
        raw_source_id = row.get('source_artifact_id')
        clean_source_id = str(raw_source_id) if raw_source_id and str(raw_source_id).strip() else None

        stmt = insert(MhtcetCollegeMetadata).values(
            college_id=college_id,
            dte_code=str(row['institute_code']),
            dte_name_raw=str(row['institute_name']),
            course_type=str(row['exam_code']),
            year=int(row['year']),
            source_artifact_id=clean_source_id
        ).on_conflict_do_update(
            constraint='uq_mhtcet_metadata_identity',
            set_={"dte_name_raw": str(row['institute_name'])}
        )
        db.execute(stmt)