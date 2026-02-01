from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
import re  # <--- Essential Import

from app.models import KCETCollegeMetadata 
from ingestion.common.interface.context_interface import ContextAdapter

class KCETContextAdapter(ContextAdapter):
    def get_exam_code(self) -> str:
        return "KCET"

    def get_state_code(self, row: Dict[str, Any]) -> Optional[str]:
        return "KA"

    def resolve_round(self, row: Dict[str, Any]) -> int:
        try:
            r = int(row.get('round'))
            if r < 1: raise ValueError
            return r
        except (TypeError, ValueError):
            raise ValueError(f"Invalid or missing round number for KCET: {row.get('round')}")

    def generate_slug(self, row: Dict[str, Any]) -> str:
        course = row['course_type_normalized'] 
        loc = row['location_type_normalized']  
        cat = row['category_raw']              
        return f"KCET_{course}_{loc}_{cat}"

    def resolve_policy_attributes(self, row: Dict[str, Any]) -> Dict[str, Any]:
        raw_cat = row['category_raw']
        is_reserved = not raw_cat.startswith("GM")
        
        return {
            "is_reserved": is_reserved,
            "category_group": self._normalize_category_group(raw_cat),
            "course_type": row['course_type_normalized'],
            "location_type": row['location_type_normalized'],
            "reservation_type": None, 
            "extra_attributes": {"raw_category_code": raw_cat}
        }

    # --- FINAL HYBRID LOGIC FOR COURSE CODES ---
    def resolve_descriptive_attributes(self, row: Dict[str, Any]) -> Dict[str, str]:
        # 1. Get raw values
        p_code = row.get('course_code_raw')
        p_name = row.get('course_name_raw', 'UNKNOWN')
        
        # 2. HYBRID LOGIC: 
        # If code is missing (2025 style), derive a stable ID from the name.
        # If code exists (2023 style), trust the official code.
        if not p_code:
            # "AI & Machine Learning" -> "AI_MACHINE_LEARNING"
            sanitized = str(p_name).upper().replace("\n", " ").strip()
            
            # Remove ' & ', '(', ')', '-', and spaces
            generated = re.sub(r'[^A-Z0-9]', '_', sanitized)
            
            # Collapse multiple underscores to one
            generated = re.sub(r'_+', '_', generated)
            
            # Clip to DB limit (60 chars is safe for String(64))
            p_code = generated.strip('_')[:60]

        return {
            "institute_code": row.get('kea_code') or 'UNKNOWN',
            "institute_name": row.get('college_name_raw') or 'UNKNOWN',
            "program_code": p_code, 
            "program_name": p_name
        }

    def upsert_exam_metadata(self, db: Session, college_id: Any, row: Dict[str, Any]):
        stmt = insert(KCETCollegeMetadata).values(
            college_id=college_id,
            kea_college_code=row['kea_code'],
            kea_college_name_raw=row['college_name_raw'],
            course_type=row['course_type_normalized'], 
            year=row['year'],
            source_artifact_id=row['source_artifact_id']
        ).on_conflict_do_update(
            constraint='uq_kcet_metadata_identity',
            set_={"kea_college_name_raw": row['college_name_raw']}
        )
        db.execute(stmt)

    def _normalize_category_group(self, raw: str) -> str:
        if raw.startswith("GM"): return "GM"
        if raw.startswith("SC"): return "SC"
        if raw.startswith("ST"): return "ST"
        if raw.startswith("1"): return "CAT-1"
        if raw.startswith("2A"): return "2A"
        if raw.startswith("2B"): return "2B"
        if raw.startswith("3A"): return "3A"
        if raw.startswith("3B"): return "3B"
        return raw