from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class BaseCutoffPlugin(ABC):
    """
    The Universal Interface (Phase 8 Final).
    Now includes Data Transformation logic to keep the Orchestrator generic.
    """

    @abstractmethod
    def get_slug(self) -> str:
        pass

    @abstractmethod
    def get_seed_urls(self) -> Dict[int, str]:
        pass

    @abstractmethod
    def get_container_tags(self) -> List[str]:
        pass

    @abstractmethod
    def get_notification_filters(self) -> Dict[str, List[str]]:
        pass

    @abstractmethod
    def get_child_filters(self) -> List[str]:
        pass

    @abstractmethod
    def normalize_round(self, text: str) -> Optional[int]:
        pass

    # --- FACTORY METHODS ---
    @abstractmethod
    def get_adapter(self) -> Any:
        """Returns the exam-specific ContextAdapter instance."""
        pass

    @abstractmethod
    def get_parser(self, pdf_path: str) -> Any:
        """Returns the exam-specific TableParser instance."""
        pass

    # --- MOVED LOGIC (The Brain) ---
    @abstractmethod
    def sanitize_round_name(self, raw_name: str) -> str:
        """
        Cleans the round name to extract the stream/course type.
        e.g. KCET: 'Second Extended Round (HK)' -> 'SECOND_EXTENDED'
        """
        pass

    @abstractmethod
    def transform_row_to_context(self, row: Dict[str, Any], artifact: Any, sanitized_stream: str) -> Dict[str, Any]:
        """
        Maps raw parser output to the standardized Context Dictionary.
        Handles logic like seat_type mapping (GENERAL -> GEN).
        """
        pass