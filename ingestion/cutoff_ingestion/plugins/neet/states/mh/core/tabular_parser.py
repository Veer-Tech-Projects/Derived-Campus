import re
import logging
import pdfplumber
import gc
from typing import Iterator, Dict, Any, List
from ingestion.cutoff_ingestion.plugins.neet.states.mh.core.row_standardizer import MHNeetRowStandardizer
from ingestion.cutoff_ingestion.plugins.neet.states.mh.core import constants as M  

logger = logging.getLogger(__name__)

class MHNeetTabularParser:
    PARSER_VERSION = "mh_medical_v4.0" # Promoted to v4.0 for structural perfection
    
    HEADER_ALIASES = {
        "sr_no": [r"(?i)sr[\.\s]*no"],
        "rank": [r"(?i)(air|sml|merit.*no|rank)"],
        "gender": [r"(?i)^g$"],
        "category": [r"(?i)cat\.?"],
        "quota": [r"(?i)quota"],
        "college": [r"(?i)code\s*college", r"(?i)college"]
    }

    def __init__(self, artifact_metadata: Dict[str, Any], pdf_path: str):
        self.metadata = artifact_metadata
        self.pdf_path = pdf_path
        self.exam_code = artifact_metadata.get("exam_slug", "UNKNOWN").upper()
        
        if "quota" not in self.metadata:
            logger.warning(f"[{self.exam_code}] Artifact metadata missing base quota. Defaulting to STATE.")
        
        self.tracker = {} 
        self.names_map = {} 
        self.last_c_code = None

    def parse(self) -> Iterator[Dict[str, Any]]:
        logger.info(f"📄 Starting MH Medical Parsing for {self.pdf_path}")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
        logger.info(f"📊 Detected {total_pages} pages. Engaging Chunked Memory Streaming...")

        CHUNK_SIZE = 50
        for chunk_start in range(0, total_pages, CHUNK_SIZE):
            chunk_end = min(chunk_start + CHUNK_SIZE, total_pages)
            
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num in range(chunk_start + 1, chunk_end + 1):
                    page_index = page_num - 1
                    page = pdf.pages[page_index]
                    
                    self.last_c_code = None
                    
                    try:
                        table = page.extract_table({
                            "vertical_strategy": "text", 
                            "horizontal_strategy": "text"
                        })
                        
                        use_fallback = False
                        col_map = {}
                        if not table or len(table) < 3:
                            use_fallback = True
                        else:
                            col_map = self._map_headers(table[:5])
                            required = {'sr_no', 'rank', 'gender', 'category', 'quota', 'college'}
                            if not required.issubset(set(col_map.keys())):
                                use_fallback = True
                            
                        if use_fallback:
                            self._parse_page_with_regex(page)
                        else:
                            self._parse_page_with_table(table, col_map)
                            
                    finally:
                        page.flush_cache()
            
            gc.collect()
            logger.info(f"♻️ Memory flushed. Processed {chunk_end}/{total_pages} pages.")
            
        for (c_code, quota, cat, g), max_rank in self.tracker.items():
            c_name = self.names_map.get(c_code, "Unknown")
            c_name = re.sub(r'-{2,}', '', c_name).strip(" -_,") 
            
            yield {
                "college_name_raw": c_name, 
                "institute_code": c_code,
                "institute_name": c_name,
                "quota_normalized": quota,
                "category_normalized": cat,
                "gender_normalized": g,
                "cutoff_rank": max_rank,
                "source_artifact_id": str(self.metadata.get("id", "")),
                "exam_code": self.exam_code,
                "year": self.metadata.get("year"),
                "round": self.metadata.get("round", 1),
                "parser_version": self.PARSER_VERSION
            }

    def _map_headers(self, header_rows: List[List[str]]) -> Dict[str, int]:
        col_map = {}
        for row in header_rows:
            if not row: continue
            for col_idx, cell in enumerate(row):
                cell_str = str(cell).strip().lower()
                if not cell_str: continue
                for std_key, patterns in self.HEADER_ALIASES.items():
                    if std_key not in col_map: 
                        if any(re.search(p, cell_str) for p in patterns):
                            col_map[std_key] = col_idx
        return col_map

    def _parse_page_with_table(self, table: List[List[str]], col_map: Dict[str, int]):
        for row in table:
            if len(row) <= max(col_map.values()): 
                self.last_c_code = None
                continue
            
            sr_no_str = str(row[col_map['sr_no']]).strip()
            
            # Determine if this is a student row or a floating text row
            try:
                _ = int(sr_no_str)
                is_student_row = True
            except ValueError:
                is_student_row = False

            if not is_student_row:
                if self.last_c_code:
                    floating_text = " ".join([str(c).strip() for c in row if c and str(c).strip()])
                    floating_text = re.sub(r'-{2,}', '', floating_text).strip(" -_,")
                    
                    # Removed hardcoded hack! Just structural headers.
                    noise_pattern = r'(?i)(Legends|Printed On|GOVERNMENT|MAHARASHTRA|Admissions|Note:|Sr\.|Roll No|CET Form|Quota|Code College|State Common|Choice|Not|Available|Retained)'
                    
                    if floating_text and not re.search(noise_pattern, floating_text):
                        if re.search(r'[A-Za-z]', floating_text): 
                            if re.match(r'^[A-Za-z0-9\(\)\.\s\-&,]+$', floating_text):
                                if floating_text not in self.names_map[self.last_c_code]:
                                    self.names_map[self.last_c_code] += f" {floating_text}"
                continue

            # --- IT IS A NEW STUDENT ROW ---
            # [ENTERPRISE FIX]: IMMEDIATELY WIPE THE MEMORY. 
            # This mathematically prevents leapfrog bleeding across invalid rows!
            self.last_c_code = None 

            rank_str = str(row[col_map['rank']]).strip()
            try: rank_val = int(rank_str)
            except ValueError: continue 
                
            college_str = str(row[col_map['college']]).strip()
            if not college_str or "Choice Not Available" in college_str or "Retained" in college_str or "Not Allotted" in college_str:
                continue
                
            c_match = re.search(r'^(\d{4,6})[:\-\s]+(.*)$', college_str)
            if not c_match: continue
                
            c_code = c_match.group(1)
            c_name = c_match.group(2).strip()
            c_name = re.sub(r'-{2,}', '', c_name).strip(" -_,")
            
            raw_quota = str(row[col_map['quota']]).strip()
            raw_cat = str(row[col_map['category']]).strip()
            raw_gender = str(row[col_map['gender']]).strip()
            
            # DIMENSIONAL FIX: Standardizer now handles all Decontamination internally!
            base_quota = self.metadata.get("quota", "STATE")
            dims = MHNeetRowStandardizer.normalize_dimensions(raw_quota, raw_cat, raw_gender, base_quota)
            
            key = (c_code, dims['quota'], dims['category'], dims['gender'])
            self.tracker[key] = max(self.tracker.get(key, 0), rank_val)
            
            if c_code not in self.names_map: 
                self.names_map[c_code] = c_name
                
            # SUCCESS. Arm the tracker for the next possible floating line.
            self.last_c_code = c_code

    def _parse_page_with_regex(self, page):
        lines = page.extract_text().split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            
            first_token = line.split()[0]
            
            # Determine if this is a student row or a floating text row
            try:
                int(first_token)
                is_student_row = True
            except ValueError:
                is_student_row = False

            if not is_student_row:
                if self.last_c_code:
                    line_clean = re.sub(r'-{2,}', '', line).strip(" -_,")
                    
                    # Removed hardcoded hack! Just structural headers.
                    noise_pattern = r'(?i)(Legends|Printed On|GOVERNMENT|MAHARASHTRA|Admissions|Note:|Sr\.|Roll No|CET Form|Quota|Code College|State Common|Choice|Not|Available|Retained)'
                    
                    if line_clean and not re.search(noise_pattern, line_clean):
                        if re.search(r'[A-Za-z]', line_clean): 
                            if re.match(r'^[A-Za-z0-9\(\)\.\s\-&,]+$', line_clean):
                                if line_clean not in self.names_map[self.last_c_code]:
                                    self.names_map[self.last_c_code] += f" {line_clean}"
                continue
                
            # --- IT IS A NEW STUDENT ROW ---
            # [ENTERPRISE FIX]: WIPE THE MEMORY to prevent leapfrog bleeding!
            self.last_c_code = None
            
            match = re.search(r'^\d+[\.\s]+(\d+)\s+.*?([MF])\s+([A-Z0-9\-\(\)\/\s]+?)\s+(\d{4,6})[:\-\s]+(.+)$', line)
            if not match: continue
                
            try: rank_val = int(match.group(1)) 
            except ValueError: continue
                
            g_raw = match.group(2).strip()
            middle_chunk = match.group(3).strip()
            c_code = match.group(4).strip()
            c_name = match.group(5).strip()
            c_name = re.sub(r'-{2,}', '', c_name).strip(" -_,")
            
            if "Choice Not Available" in c_name or "Retained" in c_name or "Not Allotted" in c_name:
                continue
            
            tokens = [t for t in middle_chunk.split() if 'EMD' not in t and 'EMR' not in t]
            if len(tokens) >= 2:
                cat_raw = tokens[0]
                # [ENTERPRISE FIX]: Prevent Candidate Category modifiers from bleeding into Quota
                modifiers = {'D1', 'D2', 'D3', 'PWD', 'HA', 'MKB', 'MINO'}
                
                if tokens[1].upper() in modifiers:
                    cat_raw = f"{tokens[0]} {tokens[1]}"
                    quota_raw = " ".join(tokens[2:]) if len(tokens) > 2 else "STATE"
                else:
                    quota_raw = " ".join(tokens[1:])
            else:
                cat_raw = tokens[0] if tokens else "OPEN"
                quota_raw = "STATE"
                
            base_quota = self.metadata.get("quota", "STATE")
            dims = MHNeetRowStandardizer.normalize_dimensions(quota_raw, cat_raw, g_raw, base_quota)
            
            key = (c_code, dims['quota'], dims['category'], dims['gender'])
            self.tracker[key] = max(self.tracker.get(key, 0), rank_val)
            
            if c_code not in self.names_map: 
                self.names_map[c_code] = c_name
                
            # SUCCESS. Arm the tracker for the next possible floating line.
            self.last_c_code = c_code