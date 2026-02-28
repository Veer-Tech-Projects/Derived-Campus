import re
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from ingestion.common.interface.context_interface import ContextAdapter
from app.models import MhtcetCollegeMetadata
from .row_standardizer import MHTCETRowStandardizer

logger = logging.getLogger(__name__)

class MHTCETContextAdapter(ContextAdapter):
    
    # Resilient Regex to capture Source and Target regardless of whitespace
    P_ALLOTTED = re.compile(r'(.+?)\s+ALLOTTED\s+TO\s+(.+)', re.IGNORECASE)
    
    def __init__(self, exam_slug: str):
        self.exam_slug = exam_slug.upper()

    def get_exam_code(self) -> str:
        return self.exam_slug

    def get_state_code(self, row: Dict[str, Any]) -> Optional[str]:
        return "MH"

    def resolve_round(self, row: Dict[str, Any]) -> int:
        try:
            r = int(row.get('round', 0))
            if r < 1: raise ValueError
            return r
        except (TypeError, ValueError):
            raise ValueError(f"Invalid or missing round number: {row.get('round')}")

    def _normalize_quota(self, row: Dict[str, Any]) -> str:
        """Deterministically resolves the core admission channel."""
        seat_type = str(row.get("seat_type", "")).upper()
        quota = str(row.get("quota", "")).upper()
        
        if seat_type == "DIPLOMA" or "DIPLOMA" in quota:
            return "DIPLOMA"
            
        # [FIX] Trust the row's actual seat_type over cached metadata
        if seat_type == "AI" or quota == "AI" or "ALL INDIA" in quota:
            return "AI"
            
        return "MH"

    def _get_location_shortcode(self, text: str) -> str:
        """Translates long government phrases into strict indexing short-codes based on a Specificity Hierarchy."""
        t = text.upper()
        # Order of Operations (Specificity Hierarchy)
        if "OTHER THAN HOME UNIVERSITY" in t: return "OHU"
        if "HOME UNIVERSITY" in t: return "HU"
        if "STATE LEVEL" in t: return "SL"
        if "ALL INDIA" in t: return "AI"
        if "MINORITY" in t: return "MIN"
        if "MAHARASHTRA" in t: return "MH" # Fallback only
        return "UNK"

    def _normalize_allocation_vector(self, row: Dict[str, Any], std_bucket: str, quota: str) -> str:
        """The Relational Engine: Uses Regex Capture to parse 'X Allotted to Y'."""
        
        # [HARDENING 1] Normalize whitespace completely before regex to ensure determinism
        raw_quota_text = str(row.get("quota_text", ""))
        quota_text = re.sub(r'\s+', ' ', raw_quota_text).upper().strip()

        # AI Override - Only bypass if there is no explicit relational distribution
        if quota == "AI" and "ALLOTTED TO" not in quota_text: 
            return "NAT" 
            
        if quota_text and quota_text != "N/A":
            match = self.P_ALLOTTED.search(quota_text)
            if match:
                src = self._get_location_shortcode(match.group(1))
                tgt = self._get_location_shortcode(match.group(2))
                
                # [HARDENING 2] Protect against UNK2UNK explosion
                if src == "UNK" and tgt == "UNK":
                    logger.error(f"VECTOR_RESOLUTION_FAILURE: Could not map source/target in '{quota_text}'")
                    
                return f"{src}2{tgt}" # e.g., 'HU2OHU'
            else:
                return self._get_location_shortcode(quota_text)

        # Enterprise Safeguard: Missing Spatial Binding Log
        if quota == "MH":
            logger.warning(f"MISSING_QUOTA_VECTOR_BINDING: No spatial quota text found. Falling back to {std_bucket}")

        return self._get_location_shortcode(std_bucket)

    def _extract_dte_code(self, raw_str: Any) -> Optional[str]:
        """Safely extracts 4 or 5 digit DTE codes without blind slicing."""
        match = re.match(r'^(\d{4,5})', str(raw_str))
        return match.group(1) if match else None

    def generate_slug(self, row: Dict[str, Any]) -> str:
        quota = self._normalize_quota(row)
        
        # 1. AI is hardcoded because it has no reservations
        if quota == "AI":
            return f"{self.exam_slug}_AI_OPEN_G"
            
        std = MHTCETRowStandardizer.decode_category_token(row.get("category_token", "OPEN"))
        
        # Deploy the Relational Vector Engine
        alloc_vector = self._normalize_allocation_vector(row, std['seat_bucket'], quota)
        gender_code = "F" if std['gender'] == "Female" else "G"
            
        slug = f"{self.exam_slug}_{quota}_{alloc_vector}_{std['category']}_{gender_code}"
        
        # --- [DYNAMIC STAGE FIX] ---
        # Future-proofs against "I-Non PWD", "I-Non Defence", "VII", etc.
        stage_raw = str(row.get("stage", "")).strip().upper()
        
        # We consider "I" (or empty) as the standard baseline seat, so no suffix is appended.
        if stage_raw and stage_raw not in ["I", "1", "NONE", "NULL"]:
            # Sanitize the string: replaces spaces/hyphens with underscores 
            # (e.g., "I-NON PWD" becomes "I_NON_PWD")
            clean_stage = re.sub(r'[^A-Z0-9]+', '_', stage_raw).strip('_')
            slug += f"_{clean_stage}"
            
        return re.sub(r'_+', '_', slug).strip('_')

    def resolve_policy_attributes(self, row: Dict[str, Any]) -> Dict[str, Any]:
        std = MHTCETRowStandardizer.decode_category_token(row.get("category_token", "OPEN"))
        quota = self._normalize_quota(row)
        alloc_vector = self._normalize_allocation_vector(row, std['seat_bucket'], quota)
            
        return {
            "is_reserved": std["category"] != "OPEN",
            "category_group": std["category"],
            "course_type": "BE" if "BE" in self.exam_slug else "PHARMA",
            "location_type": alloc_vector, 
            "reservation_type": "Supernumerary" if std.get("is_supernumerary") else "Regular",
            "extra_attributes": {
                "gender": std["gender"],
                "quota_type": quota,
                "original_seat_bucket": std["seat_bucket"],
                "raw_category_token": row.get("category_token", "OPEN"),
                "dynamic_quota_text": row.get("quota_text", "N/A") # Fidelity Preserved!
            }
        }

    def resolve_descriptive_attributes(self, row: Dict[str, Any]) -> Dict[str, str]:
        raw_dte = row.get("college_dte_code") or row.get("choice_code", "UNKNOWN")
        dte_code = self._extract_dte_code(raw_dte) or "UNKNOWN"
        
        # [FIX] Use choice_code as the program code for Tabular PDFs to prevent database collisions
        p_code = str(row.get("course_dte_code") or row.get("choice_code", "UNKNOWN"))
        
        return {
            "institute_code": dte_code,
            "institute_name": row.get("institute_name", "Unknown Institute"),
            "program_code": p_code[:60], # Safe truncation
            "program_name": row.get("course_name", "Unknown Program")
        }

    def upsert_exam_metadata(self, db: Session, college_id: Any, row: Dict[str, Any]):
        raw_dte = row.get("college_dte_code") or row.get("choice_code", "")
        dte_code = self._extract_dte_code(raw_dte)
        
        if not dte_code: return
        
        course_val = "BE" if "BE" in self.exam_slug else "PHARMA"
        
        stmt = insert(MhtcetCollegeMetadata).values(
            college_id=college_id,
            dte_code=dte_code,
            dte_name_raw=row.get("college_name_raw", "Unknown"),
            course_type=course_val,
            year=row['year'],
            source_artifact_id=row.get("source_document")
        ).on_conflict_do_nothing()
        db.execute(stmt)
        db.flush()