from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal
from dataclasses import dataclass, field
import logging
import uuid

# Configure standardized logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Classifies data for Human-in-the-Loop (HITL) workflows"""
    accepted: List[Dict] = field(default_factory=list)
    flagged: List[Dict] = field(default_factory=list) # Requires manual review
    rejected: List[Dict] = field(default_factory=list) # Invalid schema/rules

class BaseIngestionPipeline(ABC):
    """
    The Chassis: Enforces 'Fetch -> Parse -> Validate -> Store' architecture.
    Does NOT contain exam-specific logic.
    """

    def __init__(self, run_id: str, mode: Literal["bootstrap", "continuous"]):
        self.run_id = run_id
        self.mode = mode  # Critical for logic branching (e.g., skip cache in bootstrap)
        self.errors = []
        logger.info(f"Initialized Pipeline | ID: {run_id} | Mode: {mode}")

    @abstractmethod
    async def fetch_data(self) -> Any:
        """Step 1: Download raw data (PDF/HTML/API)"""
        pass

    @abstractmethod
    def parse_data(self, raw_data: Any) -> List[Dict]:
        """Step 2: Convert raw data into structured dictionaries"""
        pass

    @abstractmethod
    def validate_data(self, parsed_data: List[Dict]) -> ValidationResult:
        """Step 3: Apply quality gates. Must classify into Accepted/Flagged/Rejected."""
        pass

    @abstractmethod
    async def store_data(self, validation_result: ValidationResult):
        """Step 4: Persist data. Flagged items go to 'manual_review' bucket."""
        pass

    async def run(self):
        """Orchestrator: Executes the linear pipeline steps."""
        logger.info(f"Starting {self.__class__.__name__} execution...")
        
        try:
            # 1. Fetch
            raw = await self.fetch_data()
            if not raw:
                logger.warning("No data fetched. Aborting.")
                return

            # 2. Parse
            parsed = self.parse_data(raw)
            logger.info(f"Parsed {len(parsed)} raw records.")

            # 3. Validate (The Safety Gate)
            result = self.validate_data(parsed)
            logger.info(
                f"Validation Summary - Accepted: {len(result.accepted)}, "
                f"Flagged: {len(result.flagged)}, Rejected: {len(result.rejected)}"
            )

            # 4. Store
            await self.store_data(result)
            logger.info("Storage cycle complete.")

        except Exception as e:
            logger.error(f"Pipeline Failed: {str(e)}")
            self.errors.append(str(e))
            # In production, this would trigger PagerDuty/Sentry
            raise e
