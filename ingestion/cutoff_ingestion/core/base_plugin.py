from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from ingestion.cutoff_ingestion.core.base_scanner import BaseScanner

class BaseCutoffPlugin(ABC):
    @abstractmethod
    def get_slug(self) -> str: pass

    @abstractmethod
    def get_seed_urls(self) -> Dict[int, str]: pass

    @abstractmethod
    def get_container_tags(self) -> List[str]: pass

    @abstractmethod
    def get_scanner(self) -> BaseScanner: pass

    @abstractmethod
    def get_notification_filters(self) -> Dict[str, List[str]]: pass

    @abstractmethod
    def get_child_filters(self) -> List[str]: pass

    @abstractmethod
    def normalize_round(self, text: str) -> Optional[int]: pass

    @abstractmethod
    def get_adapter(self) -> Any: pass

    @abstractmethod
    def get_parser(self, pdf_path: str) -> Any: pass

    @abstractmethod
    def sanitize_round_name(self, raw_name: str) -> str: pass

    @abstractmethod
    def transform_row_to_context(self, row: Dict[str, Any], artifact: Any, sanitized_stream: str) -> Dict[str, Any]: pass
    
    def normalize_artifact_name(self, link_text: str) -> Any:
        return link_text.strip(), link_text.strip(), False
    
    def get_request_headers(self) -> Dict[str, str]:
        return {'User-Agent': 'DerivedBot/1.0'}
    
    def get_positive_keywords(self) -> List[str]:
        return self.get_notification_filters().get("positive", [])

    # --- PRODUCTION POLITENESS ---
    def get_politeness_delay(self) -> float:
        """Seconds to wait before network calls."""
        return 0.5