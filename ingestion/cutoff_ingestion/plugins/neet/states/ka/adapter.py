from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models import NeetCollegeMetadata 
from ingestion.common.interface.context_interface import ContextAdapter
from ingestion.cutoff_ingestion.plugins.neet.states.ka.row_standardizer import KarnatakaNEETRowStandardizer

class KarnatakaNEETContextAdapter(ContextAdapter):
    def get_exam_code(self) -> str: return "NEET_KA"
    def get_state_code(self, row: Dict[str, Any]) -> Optional[str]: return "KA"

    def resolve_round(self, row: Dict[str, Any]) -> int:
        try:
            r = int(row.get('round'))
            if r < 1: raise ValueError
            return r
        except (TypeError, ValueError):
            raise ValueError(f"Invalid or missing round for NEET_KA: {row.get('round')}")

    def generate_slug(self, row: Dict[str, Any]) -> str:
        course = row['course_normalized'] 
        seat = row['seat_type_normalized']
        loc = row['location_type_normalized']  
        cat = row['category_raw']              
        return f"NEETKA_{course}_{seat}_{loc}_{cat}"

    def resolve_policy_attributes(self, row: Dict[str, Any]) -> Dict[str, Any]:
        loc_type = row['location_type_normalized']
        if loc_type == "UNKNOWN":
            raise ValueError(f"Unrecognized Category Token: {row['category_raw']}")

        return {
            "is_reserved": KarnatakaNEETRowStandardizer.is_reserved(row['category_raw']),
            "category_group": row['category_raw'],
            "course_type": row['course_normalized'],
            "location_type": loc_type,
            "reservation_type": row['seat_type_normalized'], 
            "extra_attributes": {
                "raw_category_code": row['category_raw'],
                "raw_course_string": row['course_name_raw']
            }
        }

    def resolve_descriptive_attributes(self, row: Dict[str, Any]) -> Dict[str, str]:
        return {
            "institute_code": row.get('kea_code') or 'UNKNOWN',
            "institute_name": row.get('college_name_raw') or 'UNKNOWN',
            "program_code": f"{row['course_normalized']}_{row['seat_type_normalized']}", 
            "program_name": row.get('course_name_raw', 'UNKNOWN')
        }

    def upsert_exam_metadata(self, db: Session, college_id: Any, row: Dict[str, Any]):
        stmt = insert(NeetCollegeMetadata).values(
            college_id=college_id,
            kea_college_code=row['kea_code'],
            kea_college_name_raw=row['college_name_raw'],
            course_type=row['course_normalized'], 
            year=row['year'],
            source_artifact_id=row['source_artifact_id']
        ).on_conflict_do_update(
            constraint='uq_neet_metadata_code_year',
            set_={"kea_college_name_raw": row['college_name_raw']}
        )
        db.execute(stmt)