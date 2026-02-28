from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass

@dataclass
class ScannedArtifact:
    """
    Standardized output from any Exam Scanner.
    """
    url: str
    link_text: str
    context_header: str  # The header text (e.g. "Round 1 Cutoff")
    detected_round: int  # STRICTLY REQUIRED (Cannot be None)
    detection_method: str # e.g. "ContextMatch" or "DirectMatch"

class BaseScanner(ABC):
    """
    Strategy Interface for parsing exam-specific HTML structures.
    Decouples 'Parsing' from 'Orchestration'.
    """
    @abstractmethod
    def extract_artifacts(self, html_content: bytes, base_url: str) -> List[ScannedArtifact]:
        """
        Parses HTML and returns a list of VALID PDF artifacts.
        Must handle structural logic, filtering, and strict round detection.
        """
        pass