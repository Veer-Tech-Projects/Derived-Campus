from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from ingestion.common.interface.context_interface import ContextAdapter
from app.models import JosaaCollegeMetadata

class JosaaAdapter(ContextAdapter):
    def get_exam_code(self, row: Dict[str, Any] = None) -> str:
        if row and "exam_code" in row:
            return row["exam_code"]
        return "JOSAA"

    def get_state_code(self, row: Dict[str, Any]) -> Optional[str]:
        return "AI" # Redundant for centralized counseling

    def resolve_round(self, row: Dict[str, Any]) -> int:
        try:
            return int(row.get('round'))
        except (ValueError, TypeError):
            raise ValueError("Invalid or missing round data.")

    def generate_slug(self, row: Dict[str, Any]) -> str:
        return row.get('seat_bucket', 'UNKNOWN_BUCKET')

    def resolve_policy_attributes(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "course_type": "UG",
            "location_type": None,
            "reservation_type": row.get('quota'),
            "category_group": row.get('base_category'),
            "is_reserved": row.get('base_category', 'OPEN') != 'OPEN',
            "extra_attributes": {
                "is_pwd": row.get('is_pwd', False),
                "gender": row.get('gender_code', 'GN')
            }
        }

    def resolve_descriptive_attributes(
        self,
        row: Dict[str, Any],
        college_id: Optional[UUID] = None
    ) -> Dict[str, str]:
        if not college_id:
            raise ValueError("JoSAA descriptive resolution requires resolved college_id.")

        return {
            "institute_code": str(college_id),
            "institute_name": row.get('college_name_raw', 'UNKNOWN'),
            "program_code": row.get('program_code', 'UNKNOWN'),
            "program_name": row.get('program_name', 'UNKNOWN')
        }

    def upsert_exam_metadata(self, db: Session, college_id: UUID, row: Dict[str, Any]):
        """
        Executes idempotent metadata insert. 
        Updates source_artifact_id if a newer artifact is processed to preserve lineage.
        """
        stmt = insert(JosaaCollegeMetadata).values(
            college_id=college_id,
            institute_name_raw=row['college_name_raw'],
            institute_type=row['institute_type'],
            exam_code=row['exam_code'],
            year=row['year'],
            source_artifact_id=row['source_document']
        )
        
        stmt = stmt.on_conflict_do_update(
            constraint='uq_josaa_metadata_identity',
            set_={
                'source_artifact_id': stmt.excluded.source_artifact_id
            }
        )
        
        db.execute(stmt)
        db.flush() # Securely assigns ID while remaining inside the Universal transaction boundary