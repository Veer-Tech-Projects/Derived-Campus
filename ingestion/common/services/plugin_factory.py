from typing import Dict, List, Type
from ingestion.cutoff_ingestion.core.base_plugin import BaseCutoffPlugin

# --- KARNATAKA PLUGINS ---
from ingestion.cutoff_ingestion.plugins.kcet.plugin import KCETPlugin
from ingestion.cutoff_ingestion.plugins.neet.states.ka.plugin import KarnatakaNEETPlugin

# --- MHT-CET (ENGINEERING/PHARMA) PLUGINS ---
from ingestion.cutoff_ingestion.plugins.mhtcet.courses.be.plugin import MHTCETBTechPlugin
from ingestion.cutoff_ingestion.plugins.mhtcet.courses.pharma.plugin import MHTCETPharmaPlugin

# --- NEW: MAHARASHTRA MEDICAL PLUGINS ---
from ingestion.cutoff_ingestion.plugins.neet.states.mh.courses.ug.plugin import MHNeetUGPlugin
from ingestion.cutoff_ingestion.plugins.neet.states.mh.courses.nursing.plugin import MHNursingPlugin
from ingestion.cutoff_ingestion.plugins.neet.states.mh.courses.ayush_aiq.plugin import MHNeetAyushAiqPlugin

class PluginFactory:
    """
    Central Registry for all Exam Plugins.
    """
    _registry: Dict[str, Type[BaseCutoffPlugin]] = {
        "kcet": KCETPlugin,
        "neet_ka": KarnatakaNEETPlugin,
        "mhtcet_be": MHTCETBTechPlugin,
        "mhtcet_pharma": MHTCETPharmaPlugin,
        
        # MH Medical Hooks
        "mh_neet_ug": MHNeetUGPlugin,
        "mh_nursing": MHNursingPlugin,
        "mh_ayush_aiq": MHNeetAyushAiqPlugin
    }

    @classmethod
    def get_plugin(cls, exam_slug: str) -> BaseCutoffPlugin:
        plugin_cls = cls._registry.get(exam_slug.lower())
        if not plugin_cls:
            raise ValueError(f"Plugin not found for exam: {exam_slug}")
        return plugin_cls()

    @classmethod
    def list_available_plugins(cls) -> List[str]:
        """Returns a list of registered exam slugs"""
        return list(cls._registry.keys())