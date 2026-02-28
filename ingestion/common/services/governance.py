from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, update, func, and_
from typing import Optional, Dict, Any
import uuid

from app.models import DiscoveredArtifact

class IngestionGovernanceController:
    """
    Enforces Zero-Trust Ingestion Policies.
    Manages the lifecycle: PENDING -> APPROVED -> INGESTED.
    Updated for Phase A: Uses 'uq_artifact_identity' constraint.
    """

    def register_discovery(
        self,
        db: Session,
        pdf_path: str,
        notification_url: Optional[str],
        metadata: Dict[str, Any],
        detection_reason: str,
        source: str
    ) -> uuid.UUID:
        """
        Registers a new artifact in the Air-Lock (PENDING state).
        Idempotent: If it exists, it touches 'updated_at' but DOES NOT overwrite identity.
        """
        # 1. Determine Classification
        classification = "KNOWN_PATTERN"
        # We check specific fields to ensure we don't default to KNOWN prematurely
        if not metadata.get('year') or not metadata.get('round_name'):
            classification = "UNKNOWN_PATTERN"
        
        # 2. Upsert Artifact
        stmt = insert(DiscoveredArtifact).values(
            pdf_path=pdf_path,
            notification_url=notification_url,
            
            # --- STRICT IDENTITY MAPPING ---
            exam_code=metadata.get('exam_slug', 'UNKNOWN'), 
            original_name=metadata.get('original_name'),
            round_number=metadata.get('round'),
            
            year=metadata.get('year'),
            round_name=metadata.get('round_name'),
            seat_type=metadata.get('seat_type'),
            detection_reason=detection_reason,
            pattern_classification=classification,
            detected_source=source,
            raw_metadata=metadata,
            
            # Defaults
            status="PENDING",
            requires_reprocessing=False
        ).on_conflict_do_update(
            constraint='uq_artifact_identity',  # <--- [FIXED] Updated Constraint Name
            set_={
                # ENTERPRISE SAFETY: 
                # We do NOT overwrite exam_code, round, or original_name.
                # We only update the heartbeat and the debug metadata.
                "updated_at": func.now(),
                "raw_metadata": metadata 
            }
        ).returning(DiscoveredArtifact.id)

        return db.execute(stmt).scalar_one()

    def approve_artifact(self, db: Session, artifact_id: uuid.UUID, reviewer_email: str):
        """
        Human Action: Transitions PENDING -> APPROVED.
        Triggered by Admin Dashboard.
        """
        result = db.execute(
            update(DiscoveredArtifact)
            .where(DiscoveredArtifact.id == artifact_id)
            .where(DiscoveredArtifact.status == 'PENDING')
            .values(
                status="APPROVED",
                reviewed_by=reviewer_email,
                reviewed_at=func.now()
            )
        )
        
        if result.rowcount == 0:
            check = db.execute(
                select(DiscoveredArtifact).where(DiscoveredArtifact.id == artifact_id)
            ).scalar_one_or_none()
            
            if not check:
                raise ValueError("Artifact not found.")
            if check.status != 'PENDING':
                raise ValueError(f"Artifact is already {check.status}.")
            if check.year is None or check.round_name is None:
                raise ValueError("Cannot approve artifact: Missing Year or Round Name.")

    def mark_ingested(self, db: Session, artifact_id: uuid.UUID):
        db.execute(
            update(DiscoveredArtifact)
            .where(DiscoveredArtifact.id == artifact_id)
            .where(DiscoveredArtifact.status == 'APPROVED')
            .values(status="INGESTED")
        )
    
    def mark_failed(self, db: Session, artifact_id: uuid.UUID, error_msg: str):
        db.execute(
            update(DiscoveredArtifact)
            .where(DiscoveredArtifact.id == artifact_id)
            .values(
                status="FAILED",
                review_notes=f"System Error: {error_msg}"
            )
        )
        db.commit() # Ensure error state is persisted immediately