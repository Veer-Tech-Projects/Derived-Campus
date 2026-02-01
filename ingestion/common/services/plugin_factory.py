from ingestion.cutoff_ingestion.core.base_plugin import BaseCutoffPlugin
from ingestion.cutoff_ingestion.plugins.kcet.plugin import KCETPlugin
# Future: from ingestion.cutoff_ingestion.plugins.neet.plugin import NEETPlugin

class PluginFactory:
    """
    Centralizes plugin registration.
    Solves Audit Issue #2 (Static Registry Trap).
    """
    _REGISTRY = {
        "kcet": KCETPlugin,
        # "neet": NEETPlugin
    }

    @classmethod
    def get_plugin(cls, exam_code: str) -> BaseCutoffPlugin:
        slug = str(exam_code).lower()
        plugin_cls = cls._REGISTRY.get(slug)
        
        if not plugin_cls:
            raise ValueError(f"No plugin registered for exam: {exam_code}")
            
        return plugin_cls()