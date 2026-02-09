import uuid
import logging
from sqlalchemy.orm import Session
from sqlalchemy import delete
from app.models import (
    CutoffOutcome, 
    CollegeCandidate, 
    SeatPolicyQuarantine, 
    KCETCollegeMetadata
)

logger = logging.getLogger("JanitorService")

class JanitorService:
    """
    The 'Deep Wipe' Eraser.
    Domain: Admin Portal
    """

    @staticmethod
    def wipe_artifact(db: Session, artifact_id: uuid.UUID, exam_code: str):
        artifact_uuid = str(artifact_id)
        logger.warning(f"🧹 JANITOR: Starting Deep Wipe for {artifact_uuid} ({exam_code})")

        try:
            # 1. Universal Tables
            deleted_outcomes = db.execute(
                delete(CutoffOutcome).where(CutoffOutcome.source_document == artifact_uuid)
            ).rowcount
            
            deleted_candidates = db.execute(
                delete(CollegeCandidate)
                .where(CollegeCandidate.source_document == artifact_uuid)
                .where(CollegeCandidate.status == 'pending')
            ).rowcount

            deleted_quarantine = db.execute(
                delete(SeatPolicyQuarantine).where(SeatPolicyQuarantine.source_file == artifact_uuid)
            ).rowcount

            # 2. Selective Tables
            deleted_meta = 0
            if exam_code == "KCET":
                deleted_meta = db.execute(
                    delete(KCETCollegeMetadata)
                    .where(KCETCollegeMetadata.source_artifact_id == artifact_id)
                ).rowcount

            db.commit()
            
            logger.info(
                f"✅ JANITOR REPORT: Wiped {deleted_outcomes} outcomes, "
                f"{deleted_candidates} candidates, {deleted_quarantine} violations, "
                f"{deleted_meta} metadata rows."
            )

        except Exception as e:
            db.rollback()
            logger.error(f"❌ JANITOR FAILED: {str(e)}")
            raise e