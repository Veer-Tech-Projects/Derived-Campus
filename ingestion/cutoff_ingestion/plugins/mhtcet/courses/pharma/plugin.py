from typing import Dict
from ingestion.cutoff_ingestion.plugins.mhtcet.core.base_mhtcet_plugin import BaseMHTCETPlugin

class MHTCETPharmaPlugin(BaseMHTCETPlugin):
    
    def get_slug(self) -> str:
        return "mhtcet_pharma"

    def get_seed_urls(self) -> Dict[int, str]:
        # Validated PH Seed URLs
        return {
            2026: "https://ph2026.mahacet.org/StaticPages/HomePage",
            2025: "https://ph2025.mahacet.org/StaticPages/HomePage",
            2024: "https://ph2024.mahacet.org/StaticPages/HomePage",
            2023: "https://ph2023.maha-ara.org/StaticPages/HomePage"
        }