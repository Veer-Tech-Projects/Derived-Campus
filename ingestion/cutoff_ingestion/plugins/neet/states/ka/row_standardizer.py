import re
from typing import Tuple, Optional

class KarnatakaNEETRowStandardizer:
    """
    Standardizes NEET_KA raw data into Enterprise Facts.
    English-Only explicit ruleset.
    """

    KEA_CODE_PATTERN = re.compile(r'^([A-Z]\d{3})', re.IGNORECASE)

    # Explicit Taxonomy Mapping
    HK_CATEGORIES = {"1H", "1KH", "1RH", "2AH", "2AKH", "2ARH", "2BH", "2BKH", "2BRH", "3AH", "3AKH", "3ARH", "3BH", "3BKH", "3BRH", "GMH", "GMKH", "GMRH", "SCH", "SCKH", "SCRH", "STH", "STKH", "STRH"}
    PRIV_CATEGORIES = {"GMP", "GMPH", "MA", "MC", "ME", "MEH", "MK", "MM", "MMH", "MU", "NRI", "OPN", "OTH", "RC2", "RC3", "RC4", "RC5", "RC6", "RC7", "RC8"}
    GEN_CATEGORIES = {"1G", "1K", "1R", "2AG", "2AK", "2AR", "2BG", "2BK", "2BR", "3AG", "3AK", "3AR", "3BG", "3BK", "3BR", "GM", "GMK", "GMR", "SCG", "SCK", "SCR", "STG", "STK", "STR"}
    
    # Policy Enforcement: Explicit Unreserved List
    UNRESERVED_CATEGORIES = {"GM", "GMK", "GMR", "GMH", "GMKH", "GMRH", "GMP", "GMPH", "OPN", "NRI", "OTH"}

    @classmethod
    def get_all_valid_categories(cls) -> set:
        return cls.HK_CATEGORIES | cls.PRIV_CATEGORIES | cls.GEN_CATEGORIES

    @classmethod
    def extract_kea_code(cls, raw_code: str) -> Optional[str]:
        if not raw_code: return None
        match = cls.KEA_CODE_PATTERN.match(raw_code.strip())
        return match.group(1).upper() if match else None

    @classmethod
    def parse_course_string(cls, raw_course: str) -> Tuple[str, str]:
        """Splits 'MBBS-GOVT.' -> ('MBBS', 'GOVT')"""
        if not raw_course: return "UNKNOWN", "UNKNOWN"
        clean = raw_course.upper().replace(".", "").strip()
        parts = clean.split("-")
        
        course = parts[0].strip() if len(parts) > 0 else "UNKNOWN"
        seat_type = parts[1].strip() if len(parts) > 1 else "UNKNOWN"
        
        if seat_type == "OTHERS": seat_type = "OTH"
        
        return course, seat_type

    @classmethod
    def resolve_location_type(cls, category: str) -> str:
        cat_upper = category.upper().strip()
        if cat_upper in cls.HK_CATEGORIES: return "HK"
        if cat_upper in cls.PRIV_CATEGORIES: return "PVT"
        if cat_upper in cls.GEN_CATEGORIES: return "GEN"
        return "UNKNOWN"
        
    @classmethod
    def is_reserved(cls, category: str) -> bool:
        return category.upper().strip() not in cls.UNRESERVED_CATEGORIES