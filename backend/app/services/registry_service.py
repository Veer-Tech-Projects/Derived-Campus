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
    BOOTSTRAP = "bootstrap"       
    CONTINUOUS = "continuous"     

@dataclass
class ResolutionResult:
    college_id: Optional[uuid.UUID]
    outcome: Literal["MATCHED", "QUARANTINED"] 
    confidence: float
    reason: Optional[str] = None

class RegistryService:
    """
    The Identity Authority.
    ENTERPRISE POLICY: 
    1. Ingestion is Read-Only: We never auto-create colleges during scanning.
    2. Zero-Trust: Unknown entities are always quarantined.
    """

    @staticmethod
    def normalize_name(name: str) -> str:
        if not name: return ""
        name = name.lower().split(',')[0].split('(')[0]
        name = re.sub(r'[^a-z0-9\s]', '', name)
        return " ".join(name.split())

    def resolve_identity(
        self, 
        db: Session, 
        raw_name: str, 
        source_type: str, 
        mode: RegistryMode,
        ingestion_run_id: uuid.UUID
    ) -> ResolutionResult:
        normalized = self.normalize_name(raw_name)
        if not normalized:
             logger.warning(f"[Run: {ingestion_run_id}] Identity Resolution Failed: Empty Name")
             return ResolutionResult(None, "QUARANTINED", 0.0, "Empty/Invalid Name")

        # Step 1: Exact Alias Lookup (Read-only)
        # REJECTED AUDIT FIX: We do NOT scope by source_type. 
        # Rationale: "RVCE" is "RVCE" regardless of whether it came from KCET or COMEDK.
        # Aliases are Global Identifiers.
        existing_alias = db.execute(
            select(CollegeAlias).where(
                and_(
                    CollegeAlias.alias_name == normalized,
                    CollegeAlias.is_approved == True
                )
            )
        ).scalar_one_or_none()

        if existing_alias:
            # logger.info(f"Identity MATCH: {raw_name} -> {existing_alias.college_id}")
            return ResolutionResult(
                college_id=existing_alias.college_id,
                outcome="MATCHED",
                confidence=float(existing_alias.confidence_score or 1.0),
                reason=f"Alias Match: {normalized}"
            )

        # Step 2: STRICT QUARANTINE (No Auto-Creation)
        logger.info(f"[Run: {ingestion_run_id}] Identity QUARANTINED: {raw_name} (Norm: {normalized})")
        return ResolutionResult(
            None, 
            "QUARANTINED", 
            0.0, 
            f"Unknown identity: {raw_name}"
        )


    # --- ADMIN ACTIONS (For Phase 8) ---
    def promote_candidate(self, db: Session, raw_name: str, normalized: str, source_type: str) -> uuid.UUID:
        college_stmt = insert(College).values(
            canonical_name=raw_name, normalized_name=normalized, country_code="IN", status="active"
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

    def link_alias(self, db: Session, college_id: uuid.UUID, normalized_alias: str, source_type: str):
        stmt = insert(CollegeAlias).values(
            college_id=college_id, alias_name=normalized_alias, source_type=source_type, is_approved=True, confidence_score=1.0
        ).on_conflict_do_nothing()
        db.execute(stmt)