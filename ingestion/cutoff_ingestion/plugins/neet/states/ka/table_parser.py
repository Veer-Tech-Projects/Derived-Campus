import re
import pdfplumber
import logging
from typing import Iterator, Dict, Any, Optional
import uuid
from ingestion.cutoff_ingestion.plugins.neet.states.ka.row_standardizer import KarnatakaNEETRowStandardizer

logger = logging.getLogger(__name__)

class KarnatakaNEETTableParser:
    PARSER_VERSION = "neet_dual_v3.2" # Bumped version
    
    COLLEGE_HEADER_REGEX = re.compile(r'(?:College\s*[:\-]?)?\s*([A-Z]\d{3})\s+([A-Za-z].+)', re.IGNORECASE)
    
    def __init__(self, pdf_path: str, artifact_id: uuid.UUID, artifact_round: int):
        self.pdf_path = pdf_path
        self.artifact_id = artifact_id
        self.artifact_round = artifact_round
        
        all_cats = KarnatakaNEETRowStandardizer.get_all_valid_categories()
        cat_pattern = "|".join(all_cats)
        self.category_regex = re.compile(rf'^({cat_pattern})$', re.IGNORECASE)

    def parse(self) -> Iterator[Dict[str, Any]]:
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                engine_choice = self._route_engine(pdf)
                logger.info(f"[{self.artifact_id}] Structural Routing: Selected {engine_choice}")

                if engine_choice == "TRANSACTIONAL":
                    yield from self._run_transactional_engine(pdf)
                else:
                    yield from self._run_matrix_engine(pdf)

        except Exception as e:
            logger.error(f"Parser Crash on {self.pdf_path}: {e}")
            raise

    def _route_engine(self, pdf) -> str:
        best_score = -1
        best_engine = "MATRIX" 
        
        pages_to_scan = min(2, len(pdf.pages))
        for i in range(pages_to_scan):
            tables = pdf.pages[i].find_tables(table_settings={"vertical_strategy": "lines"})
            if not tables:
                tables = pdf.pages[i].find_tables(table_settings={"vertical_strategy": "text"})
            
            for table in tables:
                data = table.extract()
                if not data or len(data) < 2: continue
                
                header_row = [str(c).upper().strip() for c in data[0] if c]
                col_count = len(header_row)
                score = 0
                is_transactional = False
                
                if any("RANK" in h for h in header_row): score += 3
                if any("COURSE CODE" in h or "COLLEGE TYPE" in h for h in header_row): score += 3
                if col_count <= 10: 
                    score += 2
                    is_transactional = True
                
                cat_matches = sum(1 for h in header_row if self.category_regex.match(h))
                if cat_matches >= 3: 
                    score += 5
                    is_transactional = False
                if col_count > 12: score += 2

                if score > best_score:
                    best_score = score
                    best_engine = "TRANSACTIONAL" if is_transactional else "MATRIX"
                    
        return best_engine

    def _run_transactional_engine(self, pdf) -> Iterator[Dict[str, Any]]:
        agg_map = {}
        course_tracker = {}
        code_to_name_map = {} # <--- [FIX] Maps KEA Code back to real College Name
        
        for page_num, page in enumerate(pdf.pages):
            tables = pdf.pages[page_num].find_tables(table_settings={"vertical_strategy": "lines"})
            if not tables:
                tables = pdf.pages[page_num].find_tables(table_settings={"vertical_strategy": "text"})
                
            for table in tables:
                data = table.extract()
                if not data: continue
                
                header = [str(c).upper().strip() for c in data[0] if c]
                
                rank_idx = next((i for i, h in enumerate(header) if "RANK" in h), -1)
                code_idx = next((i for i, h in enumerate(header) if "CODE" in h or "TYPE" in h), -1)
                course_idx = next((i for i, h in enumerate(header) if "COURSE NAME" in h), -1)
                cat_idx = next((i for i, h in enumerate(header) if "CATEGORY" in h), -1)
                status_idx = next((i for i, h in enumerate(header) if "STATUS" in h), -1)
                round_idx = next((i for i, h in enumerate(header) if "ROUND" in h), -1)
                # Ensure we grab the name index
                name_idx = next((i for i, h in enumerate(header) if "NAME OF THE" in h or "COLLEGE ALLOTTED" in h), -1)

                if rank_idx == -1 or cat_idx == -1 or course_idx == -1: continue

                for row in data[1:]:
                    if len(row) <= max(rank_idx, cat_idx, course_idx): continue
                    
                    if round_idx != -1 and round_idx < len(row):
                        row_rnd_str = str(row[round_idx]).strip()
                        if row_rnd_str and str(self.artifact_round) not in row_rnd_str:
                            continue 
                    
                    status = str(row[status_idx]).upper() if status_idx != -1 and status_idx < len(row) else ""
                    if any(x in status for x in ["CANCEL", "SURRENDER", "NOT JOINED", "REJECT"]): 
                        continue

                    try: rank_val = int(float(str(row[rank_idx]).replace(',', '').strip()))
                    except ValueError: continue

                    c_code = str(row[code_idx]).strip() if code_idx != -1 else "UNKNOWN"
                    course_name = str(row[course_idx]).strip()
                    category = str(row[cat_idx]).strip()
                    c_name = str(row[name_idx]).strip() if name_idx != -1 else "UNKNOWN"
                    
                    if not category or not course_name: continue

                    # [FIX] Save the actual name for triage
                    if c_code != "UNKNOWN" and c_name != "UNKNOWN":
                        code_to_name_map[c_code] = c_name

                    key = (c_code, course_name, category)
                    existing_rank = agg_map.get(key, 0)
                    if rank_val > existing_rank:
                        agg_map[key] = rank_val
                        
                    c_code_base = KarnatakaNEETRowStandardizer.extract_kea_code(c_code) or c_code
                    course_tracker.setdefault(c_code_base, set()).add(course_name)

        for code, courses in course_tracker.items():
            if len(courses) > 1:
                logger.warning(f"[{self.artifact_id}] Multiple courses detected for {code}: {courses}")

        for (c_code, course_name, category), final_rank in agg_map.items():
            # [FIX] Yield the real name from our tracking map
            real_name = code_to_name_map.get(c_code, f"Unknown College ({c_code})")
            
            yield {
                "kea_code_raw": c_code,
                "college_name_raw": real_name, 
                "course_name_raw": course_name,
                "category_raw": category,
                "cutoff_rank": final_rank,
                "source_artifact_id": str(self.artifact_id),
                "parser_version": self.PARSER_VERSION
            }

    def _run_matrix_engine(self, pdf) -> Iterator[Dict[str, Any]]:
        current_college_code = None
        current_college_name = None
        last_column_count = -1
        category_map = {}

        for page_num, page in enumerate(pdf.pages):
            tables = pdf.pages[page_num].find_tables(table_settings={"vertical_strategy": "lines"})
            if not tables:
                tables = pdf.pages[page_num].find_tables(table_settings={"vertical_strategy": "text"})
                
            prev_table_bottom = 0
            
            for table in tables:
                top_bound = prev_table_bottom
                bottom_bound = table.bbox[1]
                
                if bottom_bound - top_bound > 5:
                    try:
                        crop = page.crop((0, top_bound, page.width, bottom_bound))
                        text = crop.extract_text() or ""
                        for line in text.split('\n'):
                            match = self.COLLEGE_HEADER_REGEX.search(line.strip())
                            if match:
                                current_college_code = match.group(1).upper()
                                current_college_name = match.group(2).strip()
                    except Exception: pass
                
                data = table.extract()
                prev_table_bottom = table.bbox[3]
                if not data: continue
                
                header_row = [str(c).upper().strip() if c else "" for c in data[0]]
                col_count = len(header_row)
                
                if col_count != last_column_count:
                    category_map = {} 
                    last_column_count = col_count
                
                cat_matches = sum(1 for h in header_row if h and self.category_regex.match(h))
                if cat_matches > 0:
                    category_map = {} 
                    for idx, val in enumerate(header_row):
                        if val and self.category_regex.match(val):
                            category_map[val] = idx

                if not category_map: continue
                first_cat_idx = min(category_map.values())

                for row in data[1:]:
                    if not row or len(row) <= first_cat_idx: continue
                    if not current_college_code: continue
                    
                    course_raw = str(row[first_cat_idx - 1]).strip()
                    if not course_raw: continue

                    for cat_code, col_idx in category_map.items():
                        if col_idx >= len(row): continue
                        rank_str = str(row[col_idx]).replace(',', '').strip()
                        
                        try:
                            rank_val = int(float(rank_str))
                            if rank_val > 0:
                                yield {
                                    "kea_code_raw": current_college_code,
                                    "college_name_raw": current_college_name,
                                    "course_name_raw": course_raw,
                                    "category_raw": cat_code,
                                    "cutoff_rank": rank_val,
                                    "source_artifact_id": str(self.artifact_id),
                                    "parser_version": self.PARSER_VERSION
                                }
                        except ValueError: continue 