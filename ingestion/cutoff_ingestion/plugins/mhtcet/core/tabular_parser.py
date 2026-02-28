import re
import pdfplumber
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class MHTCETTabularParser:
    
    HEADER_ALIASES = {
        "exam_type": [r"(?i).*(exam|qualfing|jee|cet).*"], 
        "closing_rank": [r"(?i).*(merit|rank).*"], 
        "choice_code": [r"(?i).*choice\s*code.*"],
        "institute_name": [r"(?i).*institute.*"],
        "course_name": [r"(?i).*course.*"],
        "seat_type": [r"(?i).*(seat\s*type|quota).*"]
    }

    def __init__(self, artifact_metadata: Dict[str, Any], pdf_path: str):
        self.metadata = artifact_metadata
        self.pdf_path = pdf_path

    def parse(self) -> List[Dict[str, Any]]:
        extracted_rows = []
        logger.info(f"📄 Starting Tabular Extraction for {self.pdf_path}")
        
        # [THE ENTERPRISE FIX] Strict Column Enforcement
        # We NEVER use 'text' for vertical_strategy because it causes column bleeding.
        # By forcing 'lines', we mathematically bind the extraction to the PDF's drawn grid.
        # High tolerance ensures it survives broken borders on page breaks.
        enterprise_table_settings = {
            "vertical_strategy": "lines", 
            "horizontal_strategy": "lines",
            "intersection_y_tolerance": 25, 
            "intersection_x_tolerance": 25
        }
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                
                tables = page.extract_tables(table_settings=enterprise_table_settings)
                if not tables: continue
                    
                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 2: continue
                    
                    header_idx = -1
                    for i, row in enumerate(table[:10]): 
                        row_text = " ".join([str(c).lower() for c in row if c])
                        if "choice code" in row_text or "institute" in row_text:
                            header_idx = i
                            break
                            
                    if header_idx == -1: continue
                        
                    headers = self._normalize_headers(table[header_idx])

                    for row in table[header_idx + 1:]:
                        row_dict = {}
                        for h, v in zip(headers, row):
                            if h == "unknown": continue
                            if h not in row_dict: 
                                row_dict[h] = v
                        
                        choice_code = str(row_dict.get("choice_code", "")).strip()
                        if not choice_code or choice_code == "None": continue 
                            
                        if "closing_rank" not in row_dict: continue

                        if "seat_type" not in row_dict:
                            if self.metadata.get("seat_type") == "DIPLOMA":
                                row_dict["seat_type"] = "DIPLOMA"
                            else:
                                row_dict["seat_type"] = self.metadata.get("quota") or "AI"
                            
                        rank, percentile = self._split_rank_percentile(row_dict.get("closing_rank", ""))
                        if rank is None: continue 
                        
                        # Data loss prevention check
                        if not row_dict.get("course_name") or not str(row_dict.get("course_name")).strip():
                            logger.warning(f"Data Loss Warning: Empty course name for {choice_code}. Dropping row.")
                            continue
                        
                        row_dict["cutoff_rank"] = rank
                        row_dict["cutoff_percentile"] = percentile
                        row_dict["round"] = self.metadata.get("round", 1)
                        extracted_rows.append(row_dict)
                        
        logger.info(f"✅ Tabular Extraction Complete. Total rows found: {len(extracted_rows)}")
        return extracted_rows

    def _normalize_headers(self, raw_headers: List[str]) -> List[str]:
        norm_headers = []
        for header in raw_headers:
            if not header:
                norm_headers.append("unknown")
                continue
            matched = False
            for std_key, patterns in self.HEADER_ALIASES.items():
                if any(re.match(p, str(header).replace('\n', ' ')) for p in patterns):
                    norm_headers.append(std_key)
                    matched = True
                    break
            if not matched: norm_headers.append("unknown")
        return norm_headers

    def _split_rank_percentile(self, text: str) -> Tuple:
        if not text or str(text).strip() in ['-', '']: return None, None
        text = str(text).replace('\n', '')
        match = re.search(r'(\d+)\s*\(([\d\.]+)\)', text)
        if match: return int(match.group(1)), float(match.group(2))
        
        digit_match = re.search(r'^(\d+)$', text.strip())
        if digit_match: return int(digit_match.group(1)), None
        return None, None