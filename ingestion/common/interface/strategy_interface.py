from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

class ValidationResult(Enum):
    """
    Enterprise-grade validation outcomes.
    This replaces simple booleans to allow for nuanced data handling.
    """
    ACCEPT = "accept"         # Data is clean; proceed to storage
    FLAG = "flag"             # Data is stored but marked with a quality warning
    QUARANTINE = "quarantine" # Data is held in a side-table for manual review
    REJECT = "reject"         # Data is structurally broken or logically impossible

@dataclass
class StandardizedRow:
    """
    The Universal DTO. 
    Standardizes data before it reaches the Identity or Storage layers.
    """
    # 1. Identity Anchors
    raw_college_name: str         
    branch_code: str              
    
    # 2. Taxonomy (Universal Slug)
    # Format: EXAM_YEAR_COURSE_LOCATION_CATEGORY
    seat_bucket_code: str         
    
    # 3. The Core Fact
    closing_rank: int             
    year: int                     
    round_number: int             
    
    # 4. Context & Metadata
    # NAMESPACE RULE: Plugin-owned keys must be prefixed (e.g., 'kcet.kea_code').
    # Engine-owned keys are reserved (e.g., 'engine.run_id').
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 5. Quality & Audit
    base_confidence: float = 1.0  
    source_file: Optional[str] = None

class IngestionStrategy(ABC):
    """
    The Plugin Contract (Strategy Pattern).
    """

    @abstractmethod
    def get_exam_slug(self) -> str:
        """Returns unique identifier (e.g., 'kcet')"""
        pass

    @abstractmethod
    async def fetch_source_data(self, year: int, round_number: int) -> Any:
        """Sourcing layer: returns raw PDF/API bytes."""
        pass

    @abstractmethod
    def parse_and_standardize(self, raw_data: Any) -> List[StandardizedRow]:
        """
        Parsing layer: Converts raw source into DTOs.
        LIFECYCLE RULES: 
        1. Errors must surface via Exceptions, not partial results.
        2. May return an empty list if no relevant data is found.
        """
        pass

    @abstractmethod
    def validate_row(self, row: StandardizedRow) -> ValidationResult:
        """
        Domain-Specific Validation Gate.
        Returns the proposal for how the Engine should handle this row.
        """
        pass