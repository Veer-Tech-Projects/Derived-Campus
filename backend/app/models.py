from sqlalchemy import (
    Column, Integer, String, Boolean, Numeric, DateTime, Text, Index, UniqueConstraint, BigInteger, ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

# --- PILLAR 2: IDENTITY RESOLUTION LAYER (LOCKED) ---

class College(Base):
    __tablename__ = "college_registry"

    college_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name = Column(Text, nullable=False)   
    normalized_name = Column(Text, nullable=False) # Constraint in __table_args__
    
    status = Column(String(32), nullable=False, server_default="active") 
    official_website = Column(Text, nullable=True)
    
    # Zero Fabrication: Nullable Geography
    country_code = Column(String(2), nullable=False, server_default="IN")
    state_code = Column(String(16), nullable=True) 
    city = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    aliases = relationship("CollegeAlias", back_populates="college")

    __table_args__ = (
        UniqueConstraint('normalized_name', name='uq_college_normalized_name'),
        Index('idx_college_normalized', 'normalized_name'), 
    )

class CollegeAlias(Base):
    __tablename__ = "college_aliases"

    alias_id = Column(BigInteger, primary_key=True, autoincrement=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id"), nullable=False)
    
    alias_name = Column(Text, nullable=False) # Constraint in __table_args__
    source_type = Column(String(64), nullable=False) 
    
    # Governance: Only True values resolve
    is_approved = Column(Boolean, nullable=False, server_default=text("false"))
    confidence_score = Column(Numeric(3, 2), nullable=True) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    college = relationship("College", back_populates="aliases")
    
    __table_args__ = (
        UniqueConstraint('alias_name', name='uq_college_alias_name'),
        Index('idx_alias_lookup', 'alias_name'),
        Index('idx_alias_approved', 'is_approved'),
    )

class CollegeCandidate(Base):
    __tablename__ = "college_candidates"

    candidate_id = Column(BigInteger, primary_key=True, autoincrement=True)
    raw_name = Column(Text, nullable=False)
    source_document = Column(Text, nullable=False)
    reason_flagged = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, server_default="pending") 
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ingestion_run_id = Column(UUID(as_uuid=True), nullable=False)

# --- PILLAR 3: CONTEXT & TAXONOMY (LOCKED) ---

class SeatBucketTaxonomy(Base):
    __tablename__ = "seat_bucket_taxonomy"

    seat_bucket_code = Column(String(128), primary_key=True)
    exam_code = Column(String(32), nullable=False, index=True)
    category_name = Column(String(64), nullable=False)
    is_reserved = Column(Boolean, nullable=False)

    course_type = Column(String(64), nullable=True)      
    location_type = Column(String(32), nullable=True)    
    reservation_type = Column(String(64), nullable=True) 

    attributes = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_taxonomy_exam_category', 'exam_code', 'category_name'),
        Index('idx_taxonomy_reserved', 'is_reserved'),
    )

class KCETCollegeMetadata(Base):
    __tablename__ = "kcet_college_metadata"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id"), nullable=False)
    kea_college_code = Column(String(16), nullable=False)
    kea_college_name_raw = Column(Text, nullable=False) 
    course_type = Column(String(32), nullable=False)    
    year = Column(Integer, nullable=False)
    source_artifact_id = Column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('college_id', 'course_type', 'year', name='uq_kcet_metadata_identity'),
        Index('idx_kcet_code_lookup', 'kea_college_code', 'year'),
        Index('idx_kcet_college_id', 'college_id'), 
    )


# --- PILLAR 1: CANONICAL FACT STORAGE (UPDATED) ---

class CutoffOutcome(Base):
    __tablename__ = "cutoff_outcomes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # --- Identity Link (NEW MANDATORY FIELD) ---
    # Links this cutoff fact to the Canonical Registry
    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id"), nullable=True)

    # --- Core Identifiers ---
    exam_code = Column(String(32), nullable=False)
    state_code = Column(String(16), nullable=True)
    year = Column(Integer, nullable=False)
    round_number = Column(Integer, nullable=False)

    # --- Institution & Program (Descriptive) ---
    institute_code = Column(String(64), nullable=False)
    institute_name = Column(Text, nullable=False)
    program_code = Column(String(64), nullable=False)
    program_name = Column(Text, nullable=False)

    # --- Seat Abstraction ---
    seat_bucket_code = Column(String(128), nullable=False) 

    # --- Outcome Metrics ---
    opening_rank = Column(Integer, nullable=True)
    closing_rank = Column(Integer, nullable=False)
    cutoff_marks = Column(Numeric(6, 2), nullable=True)
    cutoff_percentile = Column(Numeric(6, 3), nullable=True)

    # --- Temporal Control ---
    is_latest = Column(Boolean, nullable=False, server_default=text("true"))
    valid_from = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    valid_to = Column(DateTime(timezone=True), nullable=True)

    # --- Source & Trust ---
    source_authority = Column(Text, nullable=False)
    source_document = Column(Text, nullable=True)
    ingestion_run_id = Column(UUID(as_uuid=True), nullable=False)
    confidence_score = Column(Numeric(3, 2), nullable=True)
    quality_flags = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    # --- Audit ---
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(String(64), nullable=False)

    __table_args__ = (
        # Partial Unique Index for SCD Type-2 (History Support)
        Index(
            'uq_cutoff_latest_only',
            'exam_code', 'state_code', 'year', 'round_number',
            'institute_code', 'program_code', 'seat_bucket_code',
            unique=True,
            postgresql_where=text('is_latest = true')
        ),
        Index('idx_cutoff_fast_query', 'exam_code', 'state_code', 'year', 'round_number', 'is_latest'),
        Index('idx_cutoff_institute', 'institute_code', 'program_code', 'is_latest'),
        Index('idx_cutoff_rank_latest', 'closing_rank', 'is_latest'),
        Index('idx_cutoff_seat_bucket', 'seat_bucket_code'),
        Index('idx_cutoff_college_link', 'college_id'), # New Index for Identity Lookups
    )


    # --- PILLAR 4: GOVERNANCE & OBSERVABILITY (NEW) ---

class SeatPolicyQuarantine(Base):
    """
    Policy Violation Quarantine.
    Captures rows where the Seat Bucket Code (Taxonomy) is unknown or invalid
    during Continuous Mode ingestion.
    """
    __tablename__ = "seat_policy_quarantine"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Governance Context
    exam_code = Column(String(32), nullable=False, index=True)      # e.g. KCET
    seat_bucket_code = Column(String(128), nullable=False, index=True) # The unknown slug
    violation_type = Column(String(64), nullable=False)             # e.g. 'UNKNOWN_SEAT_BUCKET'

    # Source Traceability
    source_exam = Column(String(32), nullable=False)
    source_year = Column(Integer, nullable=False)
    source_round = Column(Integer, nullable=True)
    source_file = Column(Text, nullable=True)

    # Raw Input Snapshot (For Audit/Replay)
    raw_row = Column(JSONB, nullable=False)

    # Lifecycle
    status = Column(String(32), nullable=False, server_default="OPEN", index=True)
    # OPEN | ACKNOWLEDGED | RESOLVED | IGNORED

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    ingestion_run_id = Column(UUID(as_uuid=True), nullable=False)


# --- PILLAR 5: INGESTION GOVERNANCE (NEW) ---

class DiscoveredArtifact(Base):
    """
    The 'Air-Lock' table.
    Stores raw PDF links found by crawlers before they are parsed/verified.
    """
    __tablename__ = "discovered_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 1. Identity (Strict)
    # We enforce 'kcet' at the application layer, not DB layer.
    exam_code = Column(String(32), nullable=False, index=True) 
    
    # 2. Source Traceability
    pdf_path = Column(Text, nullable=False)
    notification_url = Column(Text, nullable=True)

    # 3. Audit & Sorting
    original_name = Column(Text, nullable=True)  # Zero-Inference Proof
    
    # Intentionally Nullable: If the scraper can't detect the round, 
    # we MUST still save the row (as UNKNOWN_PATTERN) for manual review.
    round_number = Column(Integer, nullable=True) 
    
    # 4. Extracted Metadata 
    year = Column(Integer, nullable=True)
    round_name = Column(Text, nullable=True)
    seat_type = Column(String(32), nullable=True)

    # 5. Discovery Context
    detection_reason = Column(Text, nullable=False)
    pattern_classification = Column(String(32), nullable=False, index=True) 
    detected_source = Column(String(32), nullable=False) 

    # 6. Governance Lifecycle
    status = Column(
        String(32), 
        server_default="PENDING", 
        nullable=False, 
        index=True
    )

    # 7. Audit & Review
    reviewed_by = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # 8. System Timestamps (Heartbeat)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # ADDED THIS COLUMN PER AUDIT RECOMMENDATION:
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    
    raw_metadata = Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)

    requires_reprocessing = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('pdf_path', 'notification_url', name='uq_discovered_pdf'),
    )


# --- PHASE 8: CONTROL PLANE GOVERNANCE (STRICT ENTERPRISE) ---

class ExamConfiguration(Base):
    """
    Global Master Switch.
    """
    __tablename__ = "exam_configuration"

    exam_code = Column(String(32), primary_key=True)
    is_active = Column(Boolean, server_default="true", nullable=False)
    ingestion_mode = Column(String(32), server_default="CONTINUOUS", nullable=False)
    config_overrides = Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    
    # Audit: Creation vs Mutation
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # [NEW FIX] Strict Mode Enforcement
        CheckConstraint(
            "ingestion_mode IN ('BOOTSTRAP', 'CONTINUOUS')",
            name="ck_exam_ingestion_mode"
        ),
    )


class IngestionRun(Base):
    """
    The Flight Recorder.
    """
    __tablename__ = "ingestion_runs"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("discovered_artifacts.id"), nullable=False)
    
    # Denormalized for fast filtering
    exam_code = Column(String(32), nullable=False)
    
    status = Column(String(32), nullable=False) 
    stats = Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    artifact = relationship("DiscoveredArtifact")

    __table_args__ = (
        # Strict Status Enforcement
        CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_ingestion_runs_status"
        ),
        Index('idx_runs_exam', 'exam_code'),
    )


class RegistryAuditLog(Base):
    """
    Compliance Log.
    """
    __tablename__ = "registry_audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    entity_type = Column(String(32), nullable=False) 
    entity_id = Column(UUID(as_uuid=True), nullable=False) 
    action = Column(String(64), nullable=False) 
    performed_by = Column(String(128), nullable=False) 
    reason = Column(Text, nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Time-based query optimization
        Index('idx_audit_timestamp', 'timestamp'),
    )