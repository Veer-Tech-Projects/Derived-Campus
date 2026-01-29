import re
import pdfplumber
import logging
from typing import Iterator, Dict, Any, List, Optional
from ingestion.cutoff_ingestion.plugins.kcet.row_standardizer import KCETRowStandardizer

logger = logging.getLogger(__name__)

class KCETTableParser:
    """
    State Machine Parser for KCET Cutoff PDFs.
    
    ENTERPRISE FEATURES:
    1. Spatial Context Awareness: Scans gaps *between* tables for floating headers.
    2. Dynamic Context Switching: Detects headers embedded *inside* tables.
    3. False Positive Guard: Verifies headers don't contain rank data.
    """
    
    PARSER_VERSION = "kcet_spatial_v2.0"

    # --- REGEX DEFINITIONS ---
    # Matches: "College: E001 University..." OR "E002 SKSJTI..."
    # Captures: Group 1 (Code), Group 2 (Name)
    COLLEGE_HEADER_REGEX = re.compile(r'(?:College\s*[:\-]?)?\s*([A-Z][0-9]{3,4})\s+([A-Za-z].+)', re.IGNORECASE)

    # Matches Category Columns (1G, 2AG, GM, SC, ST, etc.)
    CATEGORY_ANCHOR_REGEX = re.compile(r'^(\d+[A-Z]+|GM|SC|ST|C1|NRI|OPN|COMED).*', re.IGNORECASE)

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.current_college_code: Optional[str] = None
        self.current_college_name: Optional[str] = None
        self.file_seat_type: Optional[str] = None 

    def parse(self) -> Iterator[Dict[str, Any]]:
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Use find_tables to get coordinates (bbox)
                    tables = page.find_tables(table_settings={
                        "vertical_strategy": "lines", 
                        "horizontal_strategy": "lines", 
                        "snap_tolerance": 3
                    })
                    
                    if not tables: continue

                    prev_table_bottom = 0
                    
                    for table in tables:
                        # --- PHASE 1: SPATIAL SCAN (The "Gap" Fix) ---
                        # Scan the text physically located ABOVE this table but BELOW the previous one.
                        # This catches "College: E002" headers that float between tables.
                        
                        top_bound = prev_table_bottom
                        bottom_bound = table.bbox[1] # Top of current table
                        
                        # Only scan if there is a gap (e.g. > 10 units) to avoid overlapping weirdness
                        if bottom_bound - top_bound > 5:
                            try:
                                # Define area: (left, top, right, bottom)
                                crop_area = (0, top_bound, page.width, bottom_bound)
                                crop = page.crop(crop_area)
                                text_in_gap = crop.extract_text() or ""
                                self._scan_text_for_context(text_in_gap, page_num, source="SPATIAL_GAP")
                            except Exception:
                                # Cropping can fail on edge cases; ignore safely
                                pass
                        
                        # --- PHASE 2: PROCESS TABLE ---
                        # Extract data and process rows (includes the "Embedded Header" check)
                        table_data = table.extract()
                        if table_data:
                            yield from self._process_table_grid(table_data, page_num)
                        
                        # Update tracker
                        prev_table_bottom = table.bbox[3] # Bottom of current table

        except Exception as e:
            logger.error(f"Parser Crash on {self.pdf_path}: {e}")
            raise

    def _scan_text_for_context(self, text: str, page_num: int, source: str):
        """Scans a block of text to update the College Context."""
        lines = text.split('\n')
        for line in lines:
            clean_line = line.strip()
            if not clean_line or len(clean_line) < 5: continue
            if "DATE" in clean_line.upper() or "PAGE" in clean_line.upper(): continue

            match = self.COLLEGE_HEADER_REGEX.search(clean_line)
            if match:
                new_code = match.group(1).upper()
                new_name = match.group(2).strip()
                
                # Update State if changed
                if new_code != self.current_college_code:
                    logger.info(f"CONTEXT_SWITCH [{source} P{page_num}]: {self.current_college_code} -> {new_code}")
                    self.current_college_code = new_code
                    self.current_college_name = new_name
                return # Found the header, stop scanning this block

    def _determine_seat_type_from_header(self, headers: List[str]) -> str:
        valid_cats = [h.upper() for h in headers if h and self.CATEGORY_ANCHOR_REGEX.match(h)]
        if not valid_cats: return "UNKNOWN"
        
        if any(c in ['GMP', 'GMPH', 'NRI', 'OPN', 'COMED'] for c in valid_cats): return "PRIVATE"
        if any(re.match(r'^[0-9A-Z]+H$', c) for c in valid_cats): return "HK"
        return "GENERAL"

    def _find_anchor_map(self, header_row: List[str]) -> Dict[str, int]:
        category_map = {}
        found_anchor = False
        for idx, col_val in enumerate(header_row):
            if not col_val: continue
            clean_val = col_val.strip().upper()
            
            if not found_anchor and self.CATEGORY_ANCHOR_REGEX.match(clean_val): 
                found_anchor = True
            
            if found_anchor and self.CATEGORY_ANCHOR_REGEX.match(clean_val): 
                category_map[clean_val] = idx
        return category_map

    def _process_table_grid(self, table_data: List[List[str]], page_num: int) -> Iterator[Dict[str, Any]]:
        if not table_data: return
        
        # 1. Analyze Header Row
        header_row = [str(cell).strip() if cell else "" for cell in table_data[0]]
        block_seat_type = self._determine_seat_type_from_header(header_row)
        if block_seat_type == "UNKNOWN": return 

        if self.file_seat_type is None: self.file_seat_type = block_seat_type

        category_map = self._find_anchor_map(header_row)
        if not category_map: return

        first_category_idx = min(category_map.values())
        
        # 2. Iterate Data Rows
        for row in table_data[1:]:
            if not row: continue

            # --- PHASE 3: EMBEDDED CONTEXT SCAN (Backup) ---
            # Checks if a header is hidden INSIDE the table grid (merged row)
            row_text = " ".join([str(c).strip() for c in row if c])
            
            # Optimization: Only regex if row doesn't look like data
            # Check if row has numbers in category columns
            has_ranks = False
            if len(row) > first_category_idx:
                has_ranks = any(self._is_valid_rank(str(c)) for c in row[first_category_idx:])
            
            if not has_ranks:
                # Potential Header - Check Regex
                self._scan_text_for_context(row_text, page_num, source="EMBEDDED_ROW")
                # If it was a header, self.current_college_code is now updated.
                # We skip this row regardless because it's not rank data.
                continue 
            # -----------------------------------------------

            if len(row) <= first_category_idx: continue

            # 3. Audit Guard: Orphaned Data Check
            if not self.current_college_code:
                continue 

            # 4. Standardize Course
            if first_category_idx == 1:
                c_code_raw, c_name_raw = KCETRowStandardizer.merge_course_columns(row[0], "")
            else:
                course_cell = row[first_category_idx - 1]
                code_cell = row[first_category_idx - 2] if first_category_idx >= 2 else ""
                c_code_raw, c_name_raw = KCETRowStandardizer.merge_course_columns(code_cell, course_cell)

            final_code, final_name_raw, final_name_norm = KCETRowStandardizer.standardize_course(c_code_raw, c_name_raw)
            if str(final_name_raw).isdigit(): continue 

            # 5. Yield Ranks
            for cat_code, col_idx in category_map.items():
                if col_idx >= len(row): continue
                rank_val = str(row[col_idx]).replace(',', '').strip()
                
                if not self._is_valid_rank(rank_val): continue

                yield {
                    "kea_code": self.current_college_code,
                    "college_name_raw": self.current_college_name,
                    "course_code_raw": final_code,
                    "course_name_raw": final_name_raw,
                    "course_name_normalized": final_name_norm,
                    "category_raw": cat_code,
                    "seat_type": block_seat_type,
                    "cutoff_rank": rank_val,
                    "page_num": page_num,
                    "parser_version": self.PARSER_VERSION
                }

    def _is_valid_rank(self, val: str) -> bool:
        if not val or val in ["--", "-", ""]: return False
        try: 
            return float(val) > 0
        except ValueError: 
            return False