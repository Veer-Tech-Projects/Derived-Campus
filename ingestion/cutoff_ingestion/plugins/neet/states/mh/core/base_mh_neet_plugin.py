import logging
from typing import Any

from ingestion.cutoff_ingestion.plugins.neet.core.base_state_plugin import BaseNEETStatePlugin
from ingestion.cutoff_ingestion.plugins.neet.states.mh.core.scanner import MHNeetScanner
from ingestion.cutoff_ingestion.plugins.neet.states.mh.core import constants as M

logger = logging.getLogger(__name__)

class BaseMHNeetPlugin(BaseNEETStatePlugin):
    """
    The Base Contract for MH Medical (NEET UG, Nursing, AIQ).
    Implements Frozen Semantic Taxonomy for Dimensionally Safe Slugs.
    """
    
    def get_scanner(self):
        return MHNeetScanner()

    def normalize_artifact_name(self, link_text: str) -> tuple[str, str, bool]:
        """
        Builds the dimensionally safe UI Slug: 
        {EXAM_CODE}_{ROUND_TYPE}_{ROUND_SEQ}_{COURSE_GROUP}_{REVISION_TOKEN}
        (Year is intentionally excluded as it exists in the parent DB schema)
        """
        t = link_text.upper().strip()
        exam_prefix = self.get_slug().upper()
        
        # 1. Round Sequence Extraction & Normalization
        # WARNING: Uses shared M.P_ROUND_SEQ to stay perfectly synced with scanner.py
        round_seq = 0
        seq_match = M.P_ROUND_SEQ.search(t)
        if seq_match:
            r_str = seq_match.group(1).strip()
            if r_str in M.ROUND_MAP:
                round_seq = M.ROUND_MAP[r_str]
            else:
                try: 
                    round_seq = int(r_str)
                except ValueError: 
                    pass
                
        # 2. Round Type (Strict Precedence & Conditional Branching)
        round_type = "UNKNOWN_TYPE"
        if M.P_ROUND_SPECIAL_STRAY.search(t):
            round_type = "SPECIAL_STRAY"
        elif M.P_ROUND_STRAY.search(t):
            round_type = "STRAY"
        elif M.P_ROUND_INSTITUTIONAL.search(t):
            round_type = "INSTITUTIONAL"
        elif M.P_ROUND_CAP.search(t):
            round_type = "CAP"
        else:
            # THE INFERENCE RULE: Contextual CAP assumption in MH
            if round_seq > 0:
                round_type = "CAP"
                logger.info(f"Inferred CAP round from generic 'Round {round_seq}' in text: '{link_text}'")
                
        # 3. Course Group (Strict Boundaries, Explicit Fallback)
        course_group = "UNKNOWN_GROUP"
        if M.P_GROUP_MBBS_BDS.search(t):
            course_group = "MBBS_BDS"
        elif M.P_GROUP_AYUSH.search(t):
            course_group = "AYUSH"
        elif M.P_GROUP_ALLIED.search(t):
            course_group = "ALLIED"
            
        # 4. Revision Token
        revision_token = "ORIGINAL"
        if M.P_REV_REVISED.search(t):
            revision_token = "REVISED"
        elif M.P_REV_CORRIGENDUM.search(t):
            revision_token = "CORRIGENDUM"
        elif M.P_REV_SUPPLEMENTARY.search(t):
            revision_token = "SUPPLEMENTARY"
            
        # Final Assembly
        clean_slug = f"{exam_prefix}_{round_type}_{round_seq}_{course_group}_{revision_token}"
        
        # 'is_standardized' is True because this satisfies strict EDW dimensions
        return clean_slug, link_text.strip(), True


    def get_adapter(self):
        from .adapter import MHNeetContextAdapter
        return MHNeetContextAdapter(self.get_slug())

    def get_parser(self, pdf_path: str):
        pass

    def get_parser_with_context(self, pdf_path: str, artifact: Any):
        from .tabular_parser import MHNeetTabularParser
        return MHNeetTabularParser(artifact.raw_metadata or {}, pdf_path)
    
    def transform_row_to_context(self, row: dict, artifact: Any, sanitized_stream: str) -> dict:
        row['source_artifact_id'] = str(artifact.id) if artifact and hasattr(artifact, 'id') else None
        
        course_group = "UNKNOWN_COURSE"
        
        artifact_string = getattr(artifact, 'round_name', '') or getattr(artifact, 'original_name', '') or ''
        
        if artifact_string:
            # [ENTERPRISE FIX]: Replace underscores with spaces so '\b' (word boundaries) can match!
            artifact_name = str(artifact_string).upper().replace('_', ' ')
            
            if M.P_GROUP_MBBS_BDS.search(artifact_name):
                course_group = "MBBS_BDS"
            elif M.P_GROUP_AYUSH.search(artifact_name):
                course_group = "AYUSH"
            elif M.P_GROUP_ALLIED.search(artifact_name):
                course_group = "ALLIED"
                
        row['program_code'] = course_group
        return row