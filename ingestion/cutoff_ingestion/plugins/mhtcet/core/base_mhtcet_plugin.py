import re
from typing import Dict, List, Optional, Any
from ingestion.cutoff_ingestion.core.base_plugin import BaseCutoffPlugin
from ingestion.cutoff_ingestion.plugins.mhtcet.core.scanner import MHTCETScanner
from ingestion.cutoff_ingestion.plugins.mhtcet.core import constants as M

class BaseMHTCETPlugin(BaseCutoffPlugin):
    """
    The Base Contract for all Maharashtra CET Courses.
    """
    
    def get_scanner(self):
        return MHTCETScanner()

    def normalize_artifact_name(self, link_text: str) -> tuple[str, str, bool]:
        """
        Builds the deterministic slug: MHTCET_{COURSE}_R{INT}_{QUOTA}
        """
        t = link_text.upper().replace("NEW", "").strip()
        t = re.sub(r'[-‐-‒–—―_\s]+', ' ', t).replace("CUT OFF", "CUTOFF")
        
        course_slug = self.get_slug().replace("mhtcet_", "").upper()
        
        # Round Extraction
        r_match = re.search(r'ROUND\s*((?:IV|V|VI|I{1,3})|\d+)', t)
        r_str = r_match.group(1) if r_match else "0"
        
        # Strict Integer Check
        if r_str in M.ROUND_MAP:
            r_int = M.ROUND_MAP[r_str]
        else:
            try:
                r_int = int(r_str)
            except ValueError:
                r_int = 0
        
        # Quota Extraction (Specificity Hierarchy: AI before MH)
        if "DIPLOMA" in t: q = "DIPLOMA"
        elif re.search(r'\bAI\b', t) or "ALL INDIA" in t: q = "AI" 
        elif re.search(r'\bMH\b', t) or "MAHARASHTRA" in t: q = "MH"
        else: q = "UNK"
            
        clean_slug = f"MHTCET_{course_slug}_R{r_int}_{q}"
        
        return clean_slug, link_text.strip(), True

    # --- SHARED STUBS ---
    def get_container_tags(self) -> List[str]: return []
    def get_notification_filters(self) -> Dict[str, List[str]]: return {}
    def get_child_filters(self) -> List[str]: return []
    def normalize_round(self, text: str) -> Optional[int]: return None
    def sanitize_round_name(self, raw_name: str) -> str: return raw_name
    
    # --- PHASE 2 PARSER ENGINES ---
    def get_adapter(self):
        from ingestion.cutoff_ingestion.plugins.mhtcet.core.adapter import MHTCETContextAdapter
        return MHTCETContextAdapter(self.get_slug())
    
    def get_parser(self, pdf_path: str) -> Any:
        pass

    def get_parser_with_context(self, pdf_path: str, artifact: Any):
        """Dynamic self-healing routing based on Phase 1 Metadata and DB state."""
        metadata = artifact.raw_metadata or {}
        quota = metadata.get("quota", "")
        
        # [THE ORM FIX] The slug is stored in 'round_name', not 'name'!
        artifact_slug = str(getattr(artifact, 'round_name', '')).upper()
        
        if quota in ["AI", "DIPLOMA"] or "_AI" in artifact_slug or "DIPLOMA" in artifact_slug:
            from .tabular_parser import MHTCETTabularParser
            return MHTCETTabularParser(metadata, pdf_path)
        else:
            from .spatial_parser import MHTCETSpatialParser
            return MHTCETSpatialParser(metadata, pdf_path)
            
    def transform_row_to_context(self, row: Dict[str, Any], artifact: Any, sanitized_stream: str) -> Dict[str, Any]:
        """Prepares the raw parser output for the Universal Engine context manager."""
        row["exam_code"] = artifact.exam_code
        row["year"] = artifact.year
        row["round"] = artifact.round_number
        row["source_document"] = str(artifact.id)
        
        metadata = artifact.raw_metadata or {}
        artifact_slug = str(getattr(artifact, 'round_name', '')).upper()
        
        # [DATA PROTECTION & SELF-HEALING FIX]
        if not row.get("quota"):
            row["quota"] = metadata.get("quota")
            # Fallback if DB metadata is empty during re-ingestion
            if not row.get("quota"):
                if "_AI" in artifact_slug: row["quota"] = "AI"
                elif "DIPLOMA" in artifact_slug: row["quota"] = "DIPLOMA"
                else: row["quota"] = "MH"
                
        if not row.get("seat_type"):
            row["seat_type"] = metadata.get("seat_type", "REGULAR")
        
        # Safe Regex DTE Extraction
        raw_dte = str(row.get("college_dte_code") or row.get("choice_code", ""))
        dte_match = re.match(r'^(\d{4,5})', raw_dte)
        dte = dte_match.group(1) if dte_match else ""
        
        # Actively strip the "03176 - " prefix from the string
        name_raw = row.get("institute_name")
        name = str(name_raw).strip() if name_raw else "Unknown"
        name = re.sub(r'^\d{4,5}\s*-\s*', '', name).strip()
        
        row["institute_name"] = name
        row["college_name_raw"] = name
        
        return row