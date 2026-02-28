from typing import Dict
from ingestion.cutoff_ingestion.plugins.neet.states.mh.core.base_mh_neet_plugin import BaseMHNeetPlugin

class MHNeetUGPlugin(BaseMHNeetPlugin):
    """
    Handles State Quota for MBBS, BDS, BAMS, BHMS, BUMS, BPTH, etc. (Groups A, B, C)
    """
    def get_slug(self) -> str:
        return "mh_neet_ug"

    def get_seed_urls(self) -> Dict[int, str]:
        # Based on CET Cell's sub-domain naming convention for Medical UG
        return {
            2026: "https://medicalug2026.mahacet.org/NEET-UG-2026/login",
            2025: "https://medicalug2025.mahacet.org/NEET-UG-2025/login",
            2024: "https://medical2024.mahacet.org/NEET-UG-2024/login"
        }