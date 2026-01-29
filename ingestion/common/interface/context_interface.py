from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

@dataclass(frozen=True)
class ResolvedContext:
    """
    Immutable Contract.
    Contains everything the Engine needs to write the final Fact row.
    """
    college_id: UUID
    seat_bucket_code: str
    
    # Dimensions
    exam_code: str
    year: int
    round: int # NEW: Validated Round Number (No Defaults)
    state_code: Optional[str]
    
    course_type: str
    location_type: Optional[str]
    reservation_type: Optional[str]

    # Descriptive Fields (Normalized)
    institute_code: str
    institute_name: str
    program_code: str
    program_name: str

    # Traceability
    is_newly_created: bool = False

class ContextAdapter(ABC):
    """
    The Strategy Pattern Interface.
    """
    
    @abstractmethod
    def get_exam_code(self) -> str:
        pass

    @abstractmethod
    def get_state_code(self, row: Dict[str, Any]) -> Optional[str]:
        pass

    @abstractmethod
    def resolve_round(self, row: Dict[str, Any]) -> int: # NEW
        """
        Extracts and validates round number. 
        Must raise ValueError if missing or invalid.
        """
        pass

    @abstractmethod
    def generate_slug(self, row: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def resolve_policy_attributes(self, row: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def resolve_descriptive_attributes(self, row: Dict[str, Any]) -> Dict[str, str]:
        pass

    @abstractmethod
    def upsert_exam_metadata(self, db: Session, college_id: UUID, row: Dict[str, Any]):
        pass