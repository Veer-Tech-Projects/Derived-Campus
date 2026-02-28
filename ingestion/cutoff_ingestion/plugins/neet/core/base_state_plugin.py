from abc import ABC, abstractmethod
from typing import Dict, Any
from ingestion.cutoff_ingestion.core.base_plugin import BaseCutoffPlugin
from ingestion.cutoff_ingestion.core.base_scanner import BaseScanner

class BaseNEETStatePlugin(BaseCutoffPlugin, ABC):
    """
    The Federation Contract.
    All State-Level NEET Plugins (KA, TN, MH) must inherit from this.
    """
    
    @abstractmethod
    def get_scanner(self) -> BaseScanner:
        """Returns the state-specific DOM scanner."""
        pass

    # --- SHARED DEFAULTS (Can be overridden by states) ---
    def get_container_tags(self) -> list[str]:
        return [] # logic handled by Scanner internally
    
    def get_notification_filters(self) -> Dict[str, list[str]]:
        return {} # logic handled by Scanner internally
        
    def get_child_filters(self) -> list[str]:
        return [] # logic handled by Scanner internally

    # --- STUBS (To be implemented in Phase 2: Processing) ---
    def normalize_round(self, text: str) -> Any: return None
    def get_adapter(self) -> Any: raise NotImplementedError("Parser Phase Not Started")
    def get_parser(self, pdf_path: str) -> Any: raise NotImplementedError("Parser Phase Not Started")
    def sanitize_round_name(self, raw_name: str) -> str: return "UNKNOWN"
    def transform_row_to_context(self, row, artifact, stream) -> dict: return {}