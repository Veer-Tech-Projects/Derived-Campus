import re
from typing import Dict, List, Any
from ingestion.cutoff_ingestion.core.base_plugin import BaseCutoffPlugin
from ingestion.cutoff_ingestion.plugins.josaa.core.scanner import JosaaScanner
from ingestion.cutoff_ingestion.plugins.josaa.core.html_parser import JosaaGridParser

class JosaaPlugin(BaseCutoffPlugin):
    def get_slug(self) -> str:
        return "josaa"

    def get_seed_urls(self) -> Dict[int, str]:
        return {
            2025: "https://josaa.admissions.nic.in/applicant/SeatAllotmentResult/CurrentORCR.aspx",
            2024: "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx",
            2023: "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx"
        }

    def get_scanner(self):
        return JosaaScanner()

    def get_parser(self, pdf_path: str) -> Any:
        return JosaaGridParser(pdf_path)

    def get_adapter(self) -> Any:
        from .adapter import JosaaAdapter
        return JosaaAdapter()

    def transform_row_to_context(self, row: Dict[str, Any], artifact: Any, sanitized_stream: str) -> Dict[str, Any]:
        context = dict(row)
        
        context['year'] = artifact.year
        context['round'] = getattr(artifact, 'detected_round', artifact.round_number)
        context['source_document'] = str(artifact.id)

        # --- 1. Institutional Inference (Zero Hardcoding) ---
        raw_institute = row.get("college_name_raw", "")
        cleaned_inst = re.sub(r'\s+', ' ', raw_institute).strip().lower()
        
        if "indian institute of technology" in cleaned_inst:
            inst_type, exam_code = "IIT", "JEE_ADV"
        elif "institute of information technology" in cleaned_inst or "iiit" in cleaned_inst:
            inst_type, exam_code = "IIIT", "JEE_MAIN"
        elif "national institute of technology" in cleaned_inst:
            inst_type, exam_code = "NIT", "JEE_MAIN"
        else:
            inst_type, exam_code = "GFTI", "JEE_MAIN"
            
        context['institute_type'] = inst_type
        context['exam_code'] = exam_code

        # --- 2. Program Amputation & Deterministic Slugging ---
        raw_program = row.get("Academic Program Name", "")
        # Right-side regex: Only amputates the final duration/degree parentheses
        clean_program = re.sub(r'\s*\([^)]*\)$', '', raw_program).strip()
        context['program_name'] = clean_program
        
        # Deterministic slug guarantees stability against spacing/punctuation drift
        context['program_code'] = re.sub(r'[^a-z0-9]', '', clean_program.lower())[:60]

        # --- 3. Seat Bucket Synthesis & Horizontal Modifiers ---
        quota = str(row.get("Quota", "")).upper().replace(" ", "")
        raw_cat = str(row.get("Seat Type", "")).upper().strip()
        raw_gender = str(row.get("Gender", "")).upper().strip()

        # Regex separates Vertical Base Category from Horizontal Modifier (e.g. (PwD))
        cat_match = re.match(r"^(.*?)\s*(?:\((.*?)\))?$", raw_cat)
        base_cat = cat_match.group(1).replace(" ", "") if cat_match else raw_cat.replace(" ", "")
        modifier = cat_match.group(2) if cat_match and cat_match.group(2) else ""
        
        is_pwd = True if "PWD" in modifier else False
        gender_code = "F" if "FEMALE" in raw_gender else "GN"
        
        context['seat_bucket'] = f"{quota}_{base_cat}{'_PWD' if is_pwd else ''}_{gender_code}"
        context['quota'] = quota
        context['base_category'] = base_cat
        context['is_pwd'] = is_pwd
        context['gender_code'] = gender_code

        # --- 4. Safe Rank Casting (Statistical Protection) ---
        def _safe_cast(val: str):
            val = val.strip().replace("P", "") # Handle JoSAA preparatory ranks safely
            return int(val) if val.isdigit() else None
        
        context['opening_rank'] = _safe_cast(row.get("Opening Rank", ""))
        context['cutoff_rank'] = _safe_cast(row.get("cutoff_rank", "")) 
        
        return context
        
    def get_container_tags(self) -> List[str]: return []
    def get_notification_filters(self) -> Dict[str, List[str]]: return {}
    def get_child_filters(self) -> List[str]: return []
    def normalize_round(self, text: str) -> Any: return None
    def sanitize_round_name(self, raw_name: str) -> str: return raw_name