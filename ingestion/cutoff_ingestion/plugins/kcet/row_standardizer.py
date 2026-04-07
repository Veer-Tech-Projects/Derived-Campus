import re
from typing import Tuple, Optional
from ingestion.cutoff_ingestion.plugins.kcet.round_normalizer import RoundNormalizer

class KCETRowStandardizer:
    """
    Standardizes KCET raw data into Enterprise Facts.
    Enforces 'Zero-Inference' by preserving raw values.
    """

    # Matches 2-3 uppercase letters/digits (e.g., "AI", "CE", "CS") - Strict start
    COURSE_CODE_PATTERN = re.compile(r'^([A-Z0-9]{2,4})$')

    @classmethod
    def resolve_location_type(cls, category: str) -> str:
        cat_upper = str(category or "").upper().strip()

        if not cat_upper:
            return "UNKNOWN"

        # GENERAL / Rest of Karnataka
        if re.fullmatch(r"1[GKR]", cat_upper):
            return "GEN"
        if re.fullmatch(r"2A[GKR]", cat_upper):
            return "GEN"
        if re.fullmatch(r"2B[GKR]", cat_upper):
            return "GEN"
        if re.fullmatch(r"3A[GKR]", cat_upper):
            return "GEN"
        if re.fullmatch(r"3B[GKR]", cat_upper):
            return "GEN"
        if re.fullmatch(r"GM(K|R)?", cat_upper):
            return "GEN"
        if re.fullmatch(r"SC[GKR]", cat_upper):
            return "GEN"
        if re.fullmatch(r"ST[GKR]", cat_upper):
            return "GEN"

        # HK / Kalyana Karnataka
        if re.fullmatch(r"1(H|KH|RH)", cat_upper):
            return "HK"
        if re.fullmatch(r"2A(H|KH|RH)", cat_upper):
            return "HK"
        if re.fullmatch(r"2B(H|KH|RH)", cat_upper):
            return "HK"
        if re.fullmatch(r"3A(H|KH|RH)", cat_upper):
            return "HK"
        if re.fullmatch(r"3B(H|KH|RH)", cat_upper):
            return "HK"
        if re.fullmatch(r"GM(H|KH|RH|PH)", cat_upper):
            return "HK"
        if re.fullmatch(r"SC(H|KH|RH)", cat_upper):
            return "HK"
        if re.fullmatch(r"ST(H|KH|RH)", cat_upper):
            return "HK"

        # Explicit private / special
        if cat_upper in {"GMP", "OPN", "NRI", "COMED"}:
            return "PVT"

        return "UNKNOWN"

    @classmethod
    def merge_course_columns(cls, col0: str, col1: str) -> Tuple[Optional[str], str]:
        """
        Resolves Ambiguity (Issue 4):
        - Scenario A (2025): Col0="CIVIL ENGINEERING" -> Code=None, Name="CIVIL..."
        - Scenario B (2024): Col0="CE", Col1="Civil" -> Code="CE", Name="Civil"
        - Scenario C (2023): Col0="CE Civil" -> Code="CE", Name="Civil"
        """
        c0 = col0.strip()
        c1 = col1.strip()

        # Check for Scenario B (Split Columns)
        if cls.COURSE_CODE_PATTERN.match(c0) and c1:
            return c0, c1
            
        # Check for Scenario C (Merged in Col 0)
        # Regex: Code at start, followed by space and text
        split_match = re.match(r'^([A-Z0-9]{2,4})\s+(.+)$', c0)
        if split_match:
            return split_match.group(1), split_match.group(2)
            
        # Scenario A (Name Only / 2025)
        return None, c0

    @classmethod
    def standardize_course(cls, code: Optional[str], raw_name: str) -> Tuple[Optional[str], str, str]:
        """
        Final normalization.
        Returns: (Code, RawName, NormalizedName)
        """
        # If no code detected, the name is the name.
        if not code:
            return None, raw_name, raw_name
            
        # If code exists, ensure name doesn't redundantly start with it
        norm_name = raw_name
        if raw_name.startswith(code):
             norm_name = raw_name[len(code):].strip()
             
        return code, raw_name, norm_name

    @classmethod
    def standardize_round(cls, raw_round_text: str) -> Tuple[str, int]:
        norm_val = RoundNormalizer.normalize(raw_round_text)
        if norm_val is None:
             raise ValueError(f"Unknown Round Pattern: {raw_round_text}")
        return raw_round_text, norm_val