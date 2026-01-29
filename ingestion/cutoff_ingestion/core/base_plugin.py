from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class BaseCutoffPlugin(ABC):
    """
    The Universal Interface (Phase 6 Final).
    Implements the 'Block-Centric' Discovery Model.
    """

    @abstractmethod
    def get_slug(self) -> str:
        """Unique ID: 'kcet', 'neet_ka'"""
        pass

    @abstractmethod
    def get_seed_urls(self) -> Dict[int, str]:
        """Map of Year -> URL"""
        pass

    @abstractmethod
    def get_container_tags(self) -> List[str]:
        """
        Which HTML tags represent a 'Notification Block'?
        e.g., ['tr'] for tables, ['div', 'li'] for lists.
        """
        pass

    @abstractmethod
    def get_notification_filters(self) -> Dict[str, List[str]]:
        """
        STAGE 1: Strict filters for the BLOCK Header.
        {
            'positive': ['CUTOFF', 'ALLOTMENT RESULT'], 
            'negative': ['DRAFT', 'SCHEDULE']
        }
        """
        pass

    @abstractmethod
    def get_child_filters(self) -> List[str]:
        """
        STAGE 2: Relaxed negative filters for PDFs inside a valid block.
        e.g. ['FEE', 'INSTRUCTION']
        (Note: No positive filters needed here. Inheritance is automatic.)
        """
        pass

    @abstractmethod
    def normalize_round(self, text: str) -> Optional[int]:
        """Converts 'Second Extended' -> 3"""
        pass

    @abstractmethod
    def get_adapter(self) -> Any:
        pass

    @abstractmethod
    def get_parser(self, pdf_path: str) -> Any:
        pass