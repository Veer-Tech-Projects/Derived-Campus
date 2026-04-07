import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import case, func, exists

from app.models import (
    CollegeLocation, 
    CollegeLocationCandidate, 
    LocationStatusEnum, 
    LocationIngestionTracker
)
from .core.google_places_client import GooglePlacesClient

logger = logging.getLogger(__name__)

class LocationIngestionOrchestrator:
    def __init__(self, db_session_factory: sessionmaker):
        self.SessionLocal = db_session_factory
        self.client = GooglePlacesClient()

    def ingest_location(self, college_id: str, canonical_name: str, state_code: str) -> bool:
        # 1. HARD EXHAUSTION GATE
        with self.SessionLocal() as session:
            is_exhausted = session.query(
                exists().where(
                    LocationIngestionTracker.college_id == college_id,
                    LocationIngestionTracker.is_exhausted == True
                )
            ).scalar()

            if is_exhausted:
                logger.info(f"[{college_id}] 🛑 Exhaustion gate active. Skipping Serper API call.")
                return False

        # 2. STATE MACHINE OPTIMIZATION (SOFT LOCK)
        with self.SessionLocal() as session:
            is_finalized = session.query(exists().where(CollegeLocation.college_id == college_id)).scalar()
            if is_finalized:
                logger.info(f"[{college_id}] Location already canonicalized. Halting pipeline.")
                return True

            has_pending = session.query(
                exists().where(
                    CollegeLocationCandidate.college_id == college_id,
                    CollegeLocationCandidate.status == LocationStatusEnum.PENDING
                )
            ).scalar()
            if has_pending:
                logger.info(f"[{college_id}] PENDING candidate exists in Airlock. Halting pipeline.")
                return True

        # 3. NETWORK IO: GOOGLE PLACES API
        candidate_dto = self.client.search_college_location(canonical_name, state_code)

        if not candidate_dto:
            logger.warning(f"[{college_id}] No viable location candidates found by API.")
            self._increment_semantic_exhaustion(college_id)
            return False

        # 4. THE TRANSACTIONAL COMMIT
        return self._attempt_db_commit(college_id, candidate_dto)

    def _attempt_db_commit(self, college_id: str, dto) -> bool:
        with self.SessionLocal() as session:
            new_candidate = CollegeLocationCandidate(
                college_id=college_id,
                address_line=dto.raw_address,
                city=dto.parsed_city,
                district=dto.parsed_district,
                state_code=dto.parsed_state_code,
                pincode=dto.pincode,
                latitude=dto.latitude,
                longitude=dto.longitude,
                source_provider="SERPER_PLACES",
                raw_provider_payload=dto.raw_payload,
                status=LocationStatusEnum.PENDING
            )
            session.add(new_candidate)

            try:
                session.commit()
                logger.info(f"[{college_id}] Successfully secured Location Candidate.")
                return True
                
            except IntegrityError:
                session.rollback()
                logger.info(f"[{college_id}] IntegrityError: Concurrent ingestion collision.")
                return False 
                
            except OperationalError as e:
                session.rollback()
                pgcode = getattr(e.orig, "pgcode", None) if hasattr(e, "orig") else None
                is_connection_drop = pgcode is None or pgcode.startswith("08")
                
                if not is_connection_drop:
                    logger.error(f"[{college_id}] Fatal DB Rejection (pgcode: {pgcode}).")
                    return False

                logger.error(f"[{college_id}] Connection dropped. Verifying ACK-Loss.")
                try:
                    with self.SessionLocal() as check_session:
                        row_exists = check_session.query(
                            exists().where(
                                CollegeLocationCandidate.college_id == college_id,
                                CollegeLocationCandidate.status == LocationStatusEnum.PENDING
                            )
                        ).scalar()
                        return row_exists 
                except OperationalError:
                    return False

    def _increment_semantic_exhaustion(self, college_id: str):
        with self.SessionLocal() as session:
            try:
                stmt = insert(LocationIngestionTracker).values(
                    college_id=college_id, attempt_count=1, is_exhausted=False
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=['college_id'],
                    set_={
                        'attempt_count': LocationIngestionTracker.attempt_count + 1,
                        'is_exhausted': case(
                            (LocationIngestionTracker.attempt_count + 1 >= 3, True),
                            else_=LocationIngestionTracker.is_exhausted
                        ),
                        'last_attempted_at': func.now()
                    }
                )
                session.execute(stmt)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"[{college_id}] Failed to increment exhaustion tracker: {str(e)}")