import re
import pdfplumber
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MHTCETSpatialParser:
    
    P_COLLEGE = re.compile(r'^(\d{4,5})\s*-\s*(.+)')
    P_COURSE = re.compile(r'^(\d{9,10})\s*-\s*(.+)')
    P_FOOTER = re.compile(r'^(Legends|Cut[\s-]*Off Indicates|Figures in bracket)', re.IGNORECASE)
    
    def __init__(self, artifact_metadata: Dict[str, Any], pdf_path: str):
        self.metadata = artifact_metadata
        self.pdf_path = pdf_path

    def parse(self) -> List[Dict[str, Any]]:
        extracted_rows = []
        logger.info(f"📐 Starting Spatial Extraction for {self.pdf_path}")
        
        strict_settings = {
            "vertical_strategy": "lines", 
            "horizontal_strategy": "lines",
            "intersection_y_tolerance": 15, 
            "intersection_x_tolerance": 15
        }
        
        # Global Context (Maintained across page breaks)
        current_college = None
        current_college_name = "Unknown"
        current_course = None
        current_course_name = "Unknown"
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                
                text_lines = page.extract_text_lines()
                # Ensure lines are sorted strictly top-to-bottom
                text_lines.sort(key=lambda x: x["top"])
                
                tables = page.find_tables(table_settings=strict_settings)
                # Ensure tables are sorted top-to-bottom
                tables.sort(key=lambda t: t.bbox[1])
                
                line_idx = 0
                page_height = page.height
                
                for table in tables:
                    table_top = table.bbox[1]
                    
                    # [ENTERPRISE FIX] Synchronized Context Traversal
                    # Consume text lines sequentially downwards, pausing when we hit a table.
                    while line_idx < len(text_lines) and text_lines[line_idx]["bottom"] <= table_top + 5:
                        line = text_lines[line_idx]
                        txt = line["text"].strip()
                        
                        # Footer Shield
                        if line["top"] > (0.90 * page_height) and self.P_FOOTER.search(txt):
                            pass 
                        elif match := self.P_COLLEGE.match(txt):
                            current_college = match.group(1)
                            current_college_name = match.group(2).strip()
                        elif match := self.P_COURSE.match(txt):
                            current_course = match.group(1)
                            current_course_name = match.group(2).strip()
                            
                        line_idx += 1
                        
                    # 2. Process the Table using the perfectly synchronized context
                    grid = table.extract()
                    if not grid or len(grid) < 2: continue
                    
                    if not current_college or not current_course:
                        continue

                    quota_text = self._find_geometric_quota(table_top, text_lines)
                    categories = grid[0] 
                    current_stage = "I" 
                    
                    for row in grid[1:]:
                        raw_stage = str(row[0]).strip()
                        if raw_stage and raw_stage not in ["", "None", "NULL"]:
                            current_stage = raw_stage
                            
                        for col_idx in range(1, len(row)):
                            if col_idx >= len(categories): continue
                                
                            cell_data = row[col_idx]
                            if not cell_data or str(cell_data).strip() in ['-', '']: continue
                            
                            rank, percentile = self._split_cell(str(cell_data))
                            if rank is None: continue
                            
                            extracted_rows.append({
                                "college_dte_code": current_college,
                                "course_dte_code": current_course,
                                "institute_name": current_college_name,
                                "course_name": current_course_name,
                                "quota_text": quota_text,
                                "stage": current_stage, 
                                "category_token": str(categories[col_idx]).replace('\n', '').strip(),
                                "cutoff_rank": rank,
                                "closing_rank": rank,
                                "cutoff_percentile": percentile,
                                "round": self.metadata.get("round", 1)
                            })
                            
        logger.info(f"✅ Spatial Extraction Complete. Total rows found: {len(extracted_rows)}")
        return extracted_rows

    def _find_geometric_quota(self, table_top: float, text_lines: List[Dict]) -> str:
        candidates = [l for l in text_lines if l["bottom"] <= table_top + 10]
        candidates.sort(key=lambda x: x["bottom"], reverse=True)
        
        for line in candidates:
            txt = line["text"].strip()
            if not txt or txt.startswith("Status:") or txt.startswith("Stage"): continue
            if self.P_COLLEGE.match(txt) or self.P_COURSE.match(txt): continue
            return txt
        return "Unknown Quota"

    def _split_cell(self, text: str) -> tuple:
        match = re.search(r'(\d+)\s*\(([\d\.]+)\)', text.replace('\n', ' '))
        if match: return int(match.group(1)), float(match.group(2))
        return None, None