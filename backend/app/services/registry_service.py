import uuid
import re
import logging
from typing import Optional, Literal
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, and_

from app.models import College, CollegeAlias

# Enterprise Logging
logger = logging.getLogger("RegistryAuthority")

class RegistryMode(Enum):
    BOOTSTRAP = "BOOTSTRAP"       
    CONTINUOUS = "CONTINUOUS"     

@dataclass
class ResolutionResult:
    college_id: Optional[uuid.UUID]
    outcome: Literal["MATCHED", "QUARANTINED"] 
    confidence: float
    reason: Optional[str] = None

class RegistryService:
    """
    The Identity Authority.
    """
    JOSAA_SOURCE_TYPES = {"josaa_html", "josaa_pdf", "josaa"}

    @staticmethod
    def normalize_name(name: str, source_type: Optional[str] = None) -> str:
        if not name:
            return ""

        raw = str(name).strip().lower()
        source = str(source_type or "").strip().lower()

        # JoSAA-specific normalization:
        # preserve the full institute identity; do not truncate at commas/brackets.
        if source in RegistryService.JOSAA_SOURCE_TYPES:
            normalized = raw

            if "indian institute of information technology" not in normalized:
                normalized = re.sub(r"\biiit\b", "indian institute of information technology", normalized)

            if "indian institute of technology" not in normalized:
                normalized = re.sub(r"\biit\b", "indian institute of technology", normalized)

            if "national institute of technology" not in normalized:
                normalized = re.sub(r"\bnit\b", "national institute of technology", normalized)

            # Remove bracket characters but preserve enclosed identity text
            normalized = normalized.replace("(", " ").replace(")", " ")

            # Remove punctuation noise while retaining full institute identity
            normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)

            return " ".join(normalized.split())

        # Legacy/default normalization for non-JoSAA sources
        normalized = raw.split(",")[0].split("(")[0]
        normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
        return " ".join(normalized.split())


    def resolve_identity(
        self, 
        db: Session, 
        raw_name: str, 
        source_type: str, 
        mode: RegistryMode,
        ingestion_run_id: uuid.UUID
    ) -> ResolutionResult:
        normalized = self.normalize_name(raw_name, source_type=source_type)
        if not normalized:
             logger.warning(f"[Run: {ingestion_run_id}] Identity Resolution Failed: Empty Name")
             return ResolutionResult(None, "QUARANTINED", 0.0, "Empty/Invalid Name")

        existing_alias = db.execute(
            select(CollegeAlias).where(
                and_(
                    CollegeAlias.alias_name == normalized,
                    CollegeAlias.is_approved == True
                )
            )
        ).scalar_one_or_none()

        if existing_alias:
            return ResolutionResult(
                college_id=existing_alias.college_id,
                outcome="MATCHED",
                confidence=float(existing_alias.confidence_score or 1.0),
                reason=f"Alias Match: {normalized}"
            )

        logger.info(f"[Run: {ingestion_run_id}] Identity QUARANTINED: {raw_name} (Norm: {normalized})")
        return ResolutionResult(None, "QUARANTINED", 0.0, f"Unknown identity: {raw_name}")


    # --- ADMIN ACTIONS ---
    # UPDATED: Removed state_code argument
    def promote_candidate(
        self,
        db: Session,
        raw_name: str,
        normalized: str,
        source_type: str,
        origin_source_type: Optional[str] = None,
    ) -> uuid.UUID:
        effective_source_type = origin_source_type or source_type
        normalized = self.normalize_name(raw_name, source_type=effective_source_type)
        college_stmt = insert(College).values(
            canonical_name=raw_name, 
            normalized_name=normalized, 
            country_code="IN", 
            # state_code is REMOVED (defaults to NULL in DB)
            status="active"
        ).on_conflict_do_nothing(index_elements=['normalized_name']).returning(College.college_id)
        
        result_id = db.execute(college_stmt).scalar()
        if not result_id:
            result_id = db.execute(select(College.college_id).where(College.normalized_name == normalized)).scalar_one()
        
        db.flush()
        
        alias_stmt = insert(CollegeAlias).values(
            college_id=result_id, alias_name=normalized, source_type=source_type, is_approved=True, confidence_score=1.0
        ).on_conflict_do_nothing(index_elements=['alias_name'])
        db.execute(alias_stmt)
        return result_id

    def link_alias(
        self,
        db: Session,
        college_id: uuid.UUID,
        normalized_alias: str,
        source_type: str,
        origin_source_type: Optional[str] = None,
    ):
        effective_source_type = origin_source_type or source_type
        normalized_alias = self.normalize_name(normalized_alias, source_type=effective_source_type)
        stmt = insert(CollegeAlias).values(
            college_id=college_id, alias_name=normalized_alias, source_type=source_type, is_approved=True, confidence_score=1.0
        ).on_conflict_do_nothing()
        db.execute(stmt)