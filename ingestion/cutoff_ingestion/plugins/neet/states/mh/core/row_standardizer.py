import re
import logging
from typing import Dict
from ingestion.cutoff_ingestion.plugins.neet.states.mh.core import constants as M

logger = logging.getLogger(__name__)

class MHNeetRowStandardizer:
    
    @classmethod
    def normalize_dimensions(cls, raw_quota: str, raw_cat: str, raw_gender: str, base_quota: str = "STATE") -> Dict[str, str]:
        q = str(raw_quota or "").strip().upper()
        c = str(raw_cat or "").strip().upper()
        g = str(raw_gender or "").strip().upper()
        
        from ingestion.cutoff_ingestion.plugins.neet.states.mh.core import constants as M
        
        # [ENTERPRISE FIX 1]: Pre-Emptive Government Synonym Cleaners
        # Runs BEFORE any ungluers so 'PWD' doesn't accidentally trigger a false split!
        
        # 1A. Asymmetric PWD/PH Cleaner: Handles "PWD-SEB PHSEBC" -> "PHSEBC"
        q = re.sub(r'PWD-?[A-Z]*\s*PH([A-Z]*)', r'PH\1', q)
        c = re.sub(r'PWD-?[A-Z]*\s*PH([A-Z]*)', r'PH\1', c)
        
        # 1B. Modifier Bleed Cleaner: Handles "D1 DEF1" -> "DEF1"
        q = re.sub(r'D\d\s*(DEF\d)', r'\1', q)
        c = re.sub(r'D\d\s*(DEF\d)', r'\1', c)

        # [ENTERPRISE FIX 2]: Relaxed Decontamination Shield
        # Removed `" " in c` so valid spaced categories like "OBC D1" aren't falsely destroyed!
        if not g or len(g) > 1 or not c or len(c) > 12 or not q or len(q) > 14 or re.search(r'\b[MF]\b', q):
            broken_blob = f"{g} {c} {q}".strip()
            blob_match = M.P_SQUISHED_ANCHOR.search(broken_blob)
            
            if blob_match:
                g = blob_match.group(1).strip()
                remainder = blob_match.group(2).strip()
                cat_match = M.P_SQUISHED_CAT_SPLITTER.match(remainder)
                if cat_match:
                    c = cat_match.group(1).strip()
                    q = cat_match.group(2).strip()
                else:
                    c = "OPEN"
                    q = "STATE"

        # [ENTERPRISE SHIELD 3]: The "Stealth Glue" Ungluer
        if c and c not in M.MH_KNOWN_CATEGORIES and c != "STATE":
            cat_match = M.P_SQUISHED_CAT_SPLITTER.match(c)
            if cat_match:
                rem = cat_match.group(2).strip()
                rem_clean = re.sub(r'[^A-Z]', '', rem) # Ignore brackets
                if len(rem_clean) > 1: 
                    c = cat_match.group(1).strip()
                    if q in ["STATE", "", "(EMD)", "(EMR)"]:
                        q = rem

        if q and q not in M.MH_KNOWN_CATEGORIES and q != "STATE":
            q_match = M.P_SQUISHED_CAT_SPLITTER.match(q)
            if q_match:
                rem = q_match.group(2).strip()
                rem_clean = re.sub(r'[^A-Z]', '', rem)
                if len(rem_clean) > 1:
                    q = rem

        # Global cleanup of Government Accounting tags
        q = re.sub(r'\(?EM[DR]\)?', '', q).strip()
        c = re.sub(r'\(?EM[DR]\)?', '', c).strip()
        
        q_norm = re.sub(r'[\s\-\(\)]+', '', q)
        
        seat_quota = base_quota
        seat_gender = "Female" if g == "F" else "General"
        
        # 1. Generic Quotas
        if q_norm in ["STATE", "AIQ", "NRI", "INST", "MINORITY", "MNG", ""]:
            seat_quota = q_norm if q_norm else base_quota
            seat_cat = re.sub(r'[\s\-\(\)]+', '', c) if c else "OPEN"
            
            if seat_cat.endswith("W") and seat_cat not in M.MH_KNOWN_CATEGORIES:
                seat_cat = seat_cat[:-1]
                seat_gender = "Female"
            elif seat_cat.endswith("S") and seat_cat not in M.MH_KNOWN_CATEGORIES:
                seat_cat = seat_cat[:-1]
                seat_gender = "General"
        
        # 2. Specific Quotas
        else:
            if q_norm in M.MH_KNOWN_CATEGORIES:
                seat_gender = "General"
                seat_cat = q_norm
            elif q_norm.endswith("W"):
                seat_gender = "Female"
                seat_cat = q_norm[:-1]
            elif q_norm.endswith("S"): 
                seat_gender = "General"
                seat_cat = q_norm[:-1]
            else:
                seat_gender = "General"
                seat_cat = q_norm
                
        if seat_cat:
            seat_cat = re.sub(r'^(.+)\1$', r'\1', seat_cat)
                
        if seat_cat == "AIQ":
            seat_cat = "OPEN"

        if not seat_cat: 
            seat_cat = "OPEN"
        
        return {
            "quota": seat_quota,
            "category": seat_cat,
            "gender": seat_gender
        }
        
    @classmethod
    def build_seat_bucket(cls, exam_code: str, dims: Dict[str, str]) -> str:
        q = re.sub(r'[^A-Z0-9]', '', dims['quota'])
        c = re.sub(r'[^A-Z0-9]', '', dims['category'])
        g = "F" if dims['gender'] == "Female" else "G"
        return f"{exam_code.upper()}_{q}_{c}_{g}"
        
    @classmethod
    def is_reserved(cls, category: str) -> bool:
        clean_cat = re.sub(r'[^A-Z0-9]', '', category.upper())
        return clean_cat not in ["OPEN", "GENERAL", "UR", ""]