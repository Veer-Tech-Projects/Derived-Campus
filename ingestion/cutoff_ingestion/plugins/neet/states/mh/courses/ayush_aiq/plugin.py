from typing import Dict, Any
from ingestion.cutoff_ingestion.plugins.neet.states.mh.core.base_mh_neet_plugin import BaseMHNeetPlugin
from ingestion.cutoff_ingestion.plugins.neet.states.mh.core.adapter import MHNeetContextAdapter

# [ENTERPRISE FIX]: A highly specialized adapter just for AIQ to enforce geographic accuracy
class MHNeetAiqAdapter(MHNeetContextAdapter):
    def get_state_code(self, row: Dict[str, Any]) -> str:
        return "AI" # Hardcodes the State Code to All India (AI)

class MHNeetAyushAiqPlugin(BaseMHNeetPlugin):
    """
    Handles the 15% All India Quota (AIQ) for Private AYUSH colleges in Maharashtra.
    """
    def get_slug(self) -> str:
        return "mh_ayush_aiq"

    def get_seed_urls(self) -> Dict[int, str]:
        return {
            2026: "https://medicalug2026.mahacet.org/ALLINDIABAMS-2026/login",
            2025: "https://medicalug2025.mahacet.org/ALLINDIABAMS-2025/login",
            2024: "https://medical2024.mahacet.org/ALLINDIABAMS-2024/login"
        }

    # Override the adapter injection to use our specialized AIQ Adapter
    def get_adapter(self):
        return MHNeetAiqAdapter(self.get_slug())

    def transform_row_to_context(self, row: dict, artifact: Any, sanitized_stream: str) -> dict:
        # Call the base method for UUID mapping
        row = super().transform_row_to_context(row, artifact, sanitized_stream)
        
        # Override to ensure dimensional perfection for AIQ
        row['program_code'] = "AYUSH"
        row['quota_normalized'] = "AIQ" # Forces the standardizer to recognize this as an All India seat
        
        return row