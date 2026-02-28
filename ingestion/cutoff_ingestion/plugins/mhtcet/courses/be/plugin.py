from typing import Dict
from ingestion.cutoff_ingestion.plugins.mhtcet.core.base_mhtcet_plugin import BaseMHTCETPlugin

class MHTCETBTechPlugin(BaseMHTCETPlugin):
    
    def get_slug(self) -> str:
        return "mhtcet_be"

    def get_seed_urls(self) -> Dict[int, str]:
        # Validated FE Seed URLs
        return {
            2026: "https://fe2026.mahacet.org/StaticPages/HomePage",
            2025: "https://fe2025.mahacet.org/StaticPages/HomePage",
            2024: "https://fe2024.mahacet.org/StaticPages/HomePage",
            2023: "https://fe2023.maha-ara.org/StaticPages/HomePage"
        }