from typing import Dict, Any
from ingestion.cutoff_ingestion.plugins.neet.states.mh.core.base_mh_neet_plugin import BaseMHNeetPlugin

class MHNursingPlugin(BaseMHNeetPlugin):
    """
    Handles purely B.Sc. Nursing Admissions.
    """
    def get_slug(self) -> str:
        return "mh_nursing"

    def get_seed_urls(self) -> Dict[int, str]:
        # Nursing often has a dedicated portal or path
        return {
            2026: "https://medicalug2026.mahacet.org/NURSING2026/login",
            2025: "https://medicalug2025.mahacet.org/NURSING2025/login",
            2024: "https://medical2024.mahacet.org/NURSING-2024/login"
        }

    def transform_row_to_context(self, row: dict, artifact: Any, sanitized_stream: str) -> dict:
        # [ENTERPRISE FIX]: Call the base method to get the Artifact UUID mapping
        row = super().transform_row_to_context(row, artifact, sanitized_stream)
        
        # Override the base logic to strictly enforce the NURSING program code
        row['program_code'] = "NURSING"
        return row