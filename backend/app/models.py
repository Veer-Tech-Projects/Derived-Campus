import uuid
import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, Numeric, DateTime, Text, Index, UniqueConstraint, BigInteger, ForeignKey, CheckConstraint,Enum as SqEnum, ForeignKeyConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID, insert
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.database import Base


# --- RBAC ENUM ---
class AdminRole(str, enum.Enum):
    SUPERADMIN = "SUPERADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

# --- COLLEGE FILTER TOOL: SEARCH READ MODEL ENUMS ---

class SearchBuildStatusEnum(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MappingStatusEnum(str, enum.Enum):
    AUTO_APPROVED = "AUTO_APPROVED"
    APPROVED = "APPROVED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REJECTED = "REJECTED"


class FilterControlTypeEnum(str, enum.Enum):
    SELECT = "SELECT"
    AUTOCOMPLETE = "AUTOCOMPLETE"
    NUMBER_INPUT = "NUMBER_INPUT"
    HIDDEN = "HIDDEN"


class OptionSourceEnum(str, enum.Enum):
    STATIC = "STATIC"
    SERVING_MAP = "SERVING_MAP"
    LOCATION = "LOCATION"
    BRANCH = "BRANCH"
    PATH_OPTION = "PATH_OPTION"


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
        Index('idx_college_pagination', 'canonical_name', 'college_id'),
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
        Index(
            "idx_bucket_filter", 
            "exam_code", 
            "reservation_type", 
            "category_name", 
            "location_type"
        ),
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


class NeetCollegeMetadata(Base):
    __tablename__ = "neet_college_metadata"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id"), nullable=False)
    kea_college_code = Column(String(16), nullable=False)
    kea_college_name_raw = Column(Text, nullable=False) 
    course_type = Column(String(32), nullable=False)    
    year = Column(Integer, nullable=False)
    source_artifact_id = Column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('college_id', 'course_type', 'year', name='uq_neet_metadata_identity'),
        # Protects against duplicating KEA codes in the same year/course
        UniqueConstraint('kea_college_code', 'course_type', 'year', name='uq_neet_metadata_code_year'),
        Index('idx_neet_code_lookup', 'kea_college_code', 'year'),
        Index('idx_neet_college_id', 'college_id'), 
    )

class MhtcetCollegeMetadata(Base):
    __tablename__ = "mhtcet_college_metadata"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # EXACT MATCH TO YOUR SCHEMA: "college_registry.college_id"
    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id"), nullable=False)
    
    dte_code = Column(String(50), nullable=False, index=True) 
    dte_name_raw = Column(Text, nullable=False)
    course_type = Column(String(32), nullable=False)
    year = Column(Integer, nullable=False)
    source_artifact_id = Column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('dte_code', 'course_type', 'year', name='uq_mhtcet_metadata_identity'),
        Index('idx_mhtcet_code_lookup', 'dte_code', 'year'),
        Index('idx_mhtcet_college_id', 'college_id'),
    )


class JosaaCollegeMetadata(Base):
    __tablename__ = "josaa_college_metadata"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id"), nullable=False)
    
    institute_name_raw = Column(Text, nullable=False)
    institute_type = Column(String(32), nullable=False) # 'IIT', 'NIT', 'IIIT', 'GFTI'
    exam_code = Column(String(32), nullable=False)      # 'JEE_ADV', 'JEE_MAIN'
    year = Column(Integer, nullable=False)
    source_artifact_id = Column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('college_id', 'institute_name_raw', 'year', name='uq_josaa_metadata_identity'),
        Index('idx_josaa_name_lookup', 'institute_name_raw', 'year'),
        Index('idx_josaa_college_id', 'college_id'),
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
        Index(
            "idx_cutoff_filter", 
            "exam_code", 
            "seat_bucket_code", 
            "program_code",   # Shifted left for optimal prefix selectivity
            "year", 
            "round_number", 
            "college_id"
        ),
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

    # --- [NEW] INTEGRITY & MUTABILITY ---
    content_hash = Column(String(64), nullable=True)
    previous_content_hash = Column(String(64), nullable=True)
    # Use server_default=func.now() for DB-level timestamping
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('exam_code', 'year', 'pdf_path', name='uq_artifact_identity'),
        UniqueConstraint('id', 'exam_code', name='uq_discovered_artifact_id_exam'),
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
    
    # --- [NEW] RESILIENCE & ISOLATION (Phase A) ---
    # Tracks how many times we failed in a row (Circuit Breaker)
    consecutive_failure_count = Column(Integer, default=0, server_default=text('0'), nullable=False)
    
    # Locks this specific exam so Bootstrap doesn't collide with Continuous
    is_under_maintenance = Column(Boolean, default=False, server_default=text('false'), nullable=False)
    
    # Heartbeat tracker
    last_scan_at = Column(DateTime(timezone=True), nullable=True)

    metric_type = Column(String(32), server_default='rank', nullable=False)

    # Audit: Creation vs Mutation
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "ingestion_mode IN ('BOOTSTRAP', 'CONTINUOUS')",
            name="ck_exam_ingestion_mode"
        ),
        CheckConstraint(
            "metric_type IN ('rank', 'percentile')", 
            name="check_valid_metric_type"
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
        Index('idx_runs_artifact', 'artifact_id'), 
        Index('idx_runs_status', 'status'),
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
        Index('idx_audit_user', 'performed_by'),  
        Index('idx_audit_entity', 'entity_id'),
    )


# --- ADMIN USER MODEL ---
class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # RBAC & Status
    role = Column(SqEnum(AdminRole), default=AdminRole.EDITOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Security Tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Lifecycle
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    # Relationships
    audit_logs = relationship("AdminAuditTrail", back_populates="admin")

# --- AUDIT TRAIL MODEL ---
class AdminAuditTrail(Base):
    __tablename__ = "admin_audit_trail"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    
    action = Column(String(50), nullable=False, index=True)
    target_resource = Column(String(100), nullable=True)
    
    # Fix #1: Use 'default=dict' to avoid shared mutable state in Python
    details = Column(JSONB, default=dict)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    admin = relationship("AdminUser", back_populates="audit_logs")

    # Fix #3: Composite index for fast lookup of an admin's history
    __table_args__ = (
        Index("idx_admin_audit_admin_created", "admin_id", "created_at"),
    )


# --- MEDIA PIPELINE ENUMS ---
class MediaTypeEnum(str, enum.Enum):
    LOGO = "LOGO"
    CAMPUS_HERO = "CAMPUS_HERO"

class MediaStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

# --- MEDIA SOT MODEL ---
class CollegeMedia(Base):
    __tablename__ = "college_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Cascade deletion: No orphan media if a college is destroyed
    college_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("college_registry.college_id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Native PostgreSQL Enums (Set create_type=False since they exist)
    media_type = Column(SqEnum(MediaTypeEnum, name="media_type_enum", create_type=False), nullable=False)
    status = Column(SqEnum(MediaStatusEnum, name="media_status_enum", create_type=False), nullable=False)
    
    source_url = Column(Text, nullable=False)
    storage_key = Column(String, nullable=False, index=True)
    
    # The Idempotency Anchor
    content_hash = Column(String(64), nullable=False, index=True) 
    
    # File Validation Metadata
    file_size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    
    # Operational Audit Timestamp
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # 1. Active State Constraint (Existing)
        Index(
            "uq_active_college_media",
            "college_id",
            "media_type",
            unique=True,
            postgresql_where=text("status = 'ACCEPTED'")
        ),
        
        # 2. Pipeline State Lock (NEW: Ensures only 1 PENDING record exists per media type)
        Index(
            "uq_pending_college_media",
            "college_id",
            "media_type",
            unique=True,
            postgresql_where=text("status = 'PENDING'")
        ),
        
        # 3. Cryptographic Storage Idempotency (NEW: Prevents duplicate bytes per college)
        UniqueConstraint(
            "college_id", 
            "content_hash", 
            name="uq_college_content_hash"
        ),
        
        # 4. Idempotency Composite Index (Existing: Fast Hash Lookups)
        Index(
            "idx_college_media_hash_lookup", 
            "college_id", 
            "content_hash"
        ),

        Index("idx_media_lateral_fetch", "college_id", "media_type", ingested_at.desc()),
    )


# --- PHASE 8: MEDIA GOVERNANCE CONTROL PLANE ---

class MediaDispatchLock(Base):
    """
    Distributed API Idempotency Lock.
    Prevents duplicate Celery dispatch under concurrent Admin operations.
    """
    __tablename__ = "media_dispatch_locks"

    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id", ondelete="CASCADE"), primary_key=True)
    media_type = Column(String(32), primary_key=True) 
    
    locked_by = Column(String(128), nullable=False) 
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MediaIngestionTracker(Base):
    """
    Semantic Exhaustion Tracker.
    Prevents infinite loops and API burn on rural/missing colleges.
    """
    __tablename__ = "media_ingestion_tracker"

    # The composite primary key automatically creates the necessary unique index
    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id", ondelete="CASCADE"), primary_key=True)
    media_type = Column(String(32), primary_key=True)
    
    attempt_count = Column(Integer, server_default=text("0"), nullable=False)
    last_attempted_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_exhausted = Column(Boolean, server_default=text("false"), nullable=False)


# --- DOMAIN A: COURSE TYPES (Degree Framework) ---

class ExamCourseType(Base):
    __tablename__ = "exam_course_types"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    exam_code = Column(String(32), ForeignKey("exam_configuration.exam_code"), nullable=False)
    canonical_name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("id", "exam_code", name="uq_course_type_id_exam"),
        UniqueConstraint("exam_code", "normalized_name", name="uq_course_type_exam_norm"),
        
        # Format Guards (POSIX whitespace collapse)
        CheckConstraint(
            "canonical_name = regexp_replace(btrim(canonical_name), '[[:space:]]+', ' ', 'g')",
            name="chk_course_type_canonical_format"
        ),
        # Determinism Guard
        CheckConstraint(
            "normalized_name = lower(regexp_replace(btrim(canonical_name), '[[:space:]]+', ' ', 'g'))",
            name="chk_course_type_identity_determinism"
        ),
    )

class ExamCourseTypeAlias(Base):
    __tablename__ = "exam_course_type_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    exam_code = Column(String(32), nullable=False)
    course_type_id = Column(UUID(as_uuid=True), nullable=False)
    normalized_alias = Column(Text, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["course_type_id", "exam_code"], 
            ["exam_course_types.id", "exam_course_types.exam_code"],
            ondelete="CASCADE",
            name="fk_course_alias_to_registry"
        ),
        UniqueConstraint("exam_code", "normalized_alias", name="uq_course_alias_exam_norm"),
        
        CheckConstraint(
            "normalized_alias = lower(regexp_replace(btrim(normalized_alias), '[[:space:]]+', ' ', 'g'))",
            name="chk_course_alias_format"
        ),
        Index("idx_course_type_alias_parent", "course_type_id"),
    )

class ExamCourseTypeCandidate(Base):
    __tablename__ = "exam_course_type_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    exam_code = Column(String(32), nullable=False)
    raw_name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False)
    # The queue is ephemeral; APPROVED rows are physically deleted upon promotion.
    status = Column(String(16), nullable=False, server_default="PENDING")
    source_artifact_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Zero-Contention Telemetry
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["source_artifact_id", "exam_code"], 
            ["discovered_artifacts.id", "discovered_artifacts.exam_code"],
            ondelete="CASCADE",
            name="fk_course_candidate_artifact"
        ),
        UniqueConstraint("exam_code", "normalized_name", name="uq_course_candidate_exam_norm"),
        
        CheckConstraint("length(btrim(raw_name)) > 0", name="chk_course_cand_raw_not_empty"),
        CheckConstraint(
            "normalized_name = lower(regexp_replace(btrim(normalized_name), '[[:space:]]+', ' ', 'g'))",
            name="chk_course_cand_norm_format"
        ),
        CheckConstraint("status IN ('PENDING', 'REJECTED')", name="chk_course_cand_status"),
        Index("idx_course_candidate_status_time", "exam_code", "status", "created_at"),
    )


# --- DOMAIN B: BRANCHES (Discipline & Variant) ---

class ExamBranchRegistry(Base):
    __tablename__ = "exam_branch_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    exam_code = Column(String(32), ForeignKey("exam_configuration.exam_code"), nullable=False)
    discipline = Column(Text, nullable=False)
    variant = Column(Text, nullable=True)
    normalized_name = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("id", "exam_code", name="uq_branch_registry_id_exam"),
        UniqueConstraint("exam_code", "normalized_name", name="uq_branch_registry_exam_norm"),
        
        # PostgreSQL NULL-Safe Unique Indexes
        Index(
            "idx_branch_var_notnull", 
            "exam_code", text("lower(discipline)"), text("lower(variant)"), 
            unique=True, postgresql_where=text("variant IS NOT NULL")
        ),
        Index(
            "idx_branch_var_null", 
            "exam_code", text("lower(discipline)"), 
            unique=True, postgresql_where=text("variant IS NULL")
        ),
        
        # Format Guards
        CheckConstraint(
            "discipline = regexp_replace(btrim(discipline), '[[:space:]]+', ' ', 'g')",
            name="chk_branch_discipline_format"
        ),
        CheckConstraint(
            "variant IS NULL OR variant = regexp_replace(btrim(variant), '[[:space:]]+', ' ', 'g')",
            name="chk_branch_variant_format"
        ),
        # Determinism Guard
        CheckConstraint(
            "normalized_name = lower(regexp_replace(btrim(discipline), '[[:space:]]+', ' ', 'g')) || COALESCE(' - ' || lower(regexp_replace(btrim(variant), '[[:space:]]+', ' ', 'g')), '')",
            name="chk_branch_identity_determinism"
        ),
        Index("idx_branch_registry_discipline", "exam_code", "discipline"),
    )

class ExamBranchAlias(Base):
    __tablename__ = "exam_branch_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    exam_code = Column(String(32), nullable=False)
    branch_id = Column(UUID(as_uuid=True), nullable=False)
    normalized_alias = Column(Text, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["branch_id", "exam_code"], 
            ["exam_branch_registry.id", "exam_branch_registry.exam_code"],
            ondelete="CASCADE",
            name="fk_branch_alias_to_registry"
        ),
        UniqueConstraint("exam_code", "normalized_alias", name="uq_branch_alias_exam_norm"),
        
        CheckConstraint(
            "normalized_alias = lower(regexp_replace(btrim(normalized_alias), '[[:space:]]+', ' ', 'g'))",
            name="chk_branch_alias_format"
        ),
        Index("idx_branch_alias_parent", "branch_id"),
    )

class ExamBranchCandidate(Base):
    __tablename__ = "exam_branch_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    exam_code = Column(String(32), nullable=False)
    raw_name = Column(Text, nullable=False)
    normalized_name = Column(Text, nullable=False)
    # The queue is ephemeral; APPROVED rows are physically deleted upon promotion.
    status = Column(String(16), nullable=False, server_default="PENDING")
    source_artifact_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Zero-Contention Telemetry
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["source_artifact_id", "exam_code"], 
            ["discovered_artifacts.id", "discovered_artifacts.exam_code"],
            ondelete="CASCADE",
            name="fk_branch_candidate_artifact"
        ),
        UniqueConstraint("exam_code", "normalized_name", name="uq_branch_candidate_exam_norm"),
        
        CheckConstraint("length(btrim(raw_name)) > 0", name="chk_branch_cand_raw_not_empty"),
        CheckConstraint(
            "normalized_name = lower(regexp_replace(btrim(normalized_name), '[[:space:]]+', ' ', 'g'))",
            name="chk_branch_cand_norm_format"
        ),
        CheckConstraint("status IN ('PENDING', 'REJECTED')", name="chk_branch_cand_status"),
        Index("idx_branch_candidate_status_time", "exam_code", "status", "created_at"),
    )


# --- PHASE 9: LOCATION ENRICHMENT PIPELINE (STUDENT FILTER TOOL) ---

class LocationStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class CollegeLocation(Base):
    """
    Canonical Master Table for Geocoding and Address Data.
    Strictly 1-to-1 with College Registry.
    """
    __tablename__ = "college_locations"

    # college_id acts as both PK and FK, guaranteeing strict 1-to-1 relationship
    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id", ondelete="CASCADE"), primary_key=True)
    
    address_line = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    state_code = Column(String(16), nullable=True)
    pincode = Column(String(20), nullable=True)
    
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        # High-performance Filter Tool Indexes
        Index('idx_location_state_city', 'state_code', 'city'),
        Index('idx_location_district', 'district'),
        Index('idx_location_pincode', 'pincode'),
    )


class CollegeLocationCandidate(Base):
    """
    The Quarantine Airlock for Google Places API responses.
    Awaiting Human-in-the-Loop verification.
    """
    __tablename__ = "college_location_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Parsed structured data (Editable in Admin UI)
    address_line = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    state_code = Column(String(16), nullable=True)
    pincode = Column(String(20), nullable=True)
    
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)

    # Governance & Audit
    source_provider = Column(String(64), nullable=False)  # e.g., 'SERPER_PLACES'
    raw_provider_payload = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    
    # [FIXED] Native PostgreSQL Enum instead of String + CheckConstraint
    status = Column(SqEnum(LocationStatusEnum, name="location_status_enum"), nullable=False, server_default=LocationStatusEnum.PENDING.value) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        # Ensure only one PENDING candidate exists per college to prevent UI spam
        Index(
            "uq_pending_location_candidate",
            "college_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'")
        ),
    )


class LocationDispatchLock(Base):
    """
    Distributed API Idempotency Lock for Location Pipeline.
    Prevents duplicate Celery dispatch under concurrent Admin operations.
    """
    __tablename__ = "location_dispatch_locks"

    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id", ondelete="CASCADE"), primary_key=True)
    locked_by = Column(String(128), nullable=False) 
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LocationIngestionTracker(Base):
    """
    Semantic Exhaustion Tracker.
    Prevents infinite API burn on rural colleges that Google Maps doesn't know about.
    """
    __tablename__ = "location_ingestion_tracker"

    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id", ondelete="CASCADE"), primary_key=True)
    attempt_count = Column(Integer, server_default=text("0"), nullable=False)
    last_attempted_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_exhausted = Column(Boolean, server_default=text("false"), nullable=False)



# --- COLLEGE FILTER TOOL: EXAM PATH METADATA ---

class ExamPathCatalog(Base):
    __tablename__ = "exam_path_catalog"

    path_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_path_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_path_catalog.path_id", ondelete="SET NULL"),
        nullable=True
    )

    path_key = Column(String(64), nullable=False)
    visible_label = Column(String(128), nullable=False)

    exam_family = Column(String(64), nullable=False)
    resolved_exam_code = Column(String(32), nullable=True)

    education_type = Column(String(64), nullable=True)
    selection_type = Column(String(64), nullable=True)

    metric_type = Column(String(32), nullable=False)
    expected_max_rounds = Column(Integer, nullable=False)

    supports_branch = Column(Boolean, nullable=False, server_default=text("false"))
    supports_course_relaxation = Column(Boolean, nullable=False, server_default=text("false"))
    supports_location_filter = Column(Boolean, nullable=False, server_default=text("true"))
    supports_opening_rank = Column(Boolean, nullable=False, server_default=text("false"))

    active = Column(Boolean, nullable=False, server_default=text("true"))
    display_order = Column(Integer, nullable=False, server_default=text("0"))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    parent = relationship("ExamPathCatalog", remote_side=[path_id])

    __table_args__ = (
        UniqueConstraint("path_key", name="uq_exam_path_catalog_path_key"),
        CheckConstraint("metric_type IN ('rank', 'percentile')", name="ck_exam_path_metric_type"),
        CheckConstraint("expected_max_rounds > 0", name="ck_exam_path_expected_max_rounds_positive"),
        Index("idx_exam_path_active_order", "active", "display_order"),
        Index("idx_exam_path_family", "exam_family"),
    )


class ExamPathFilterSchema(Base):
    __tablename__ = "exam_path_filter_schema"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_path_catalog.path_id", ondelete="CASCADE"),
        nullable=False
    )

    filter_key = Column(String(64), nullable=False)
    filter_label = Column(String(128), nullable=False)

    control_type = Column(
        SqEnum(FilterControlTypeEnum, name="filter_control_type_enum"),
        nullable=False
    )
    option_source = Column(
        SqEnum(OptionSourceEnum, name="filter_option_source_enum"),
        nullable=False
    )

    is_required = Column(Boolean, nullable=False, server_default=text("false"))
    is_visible = Column(Boolean, nullable=False, server_default=text("true"))
    is_auto_fillable = Column(Boolean, nullable=False, server_default=text("false"))

    sort_order = Column(Integer, nullable=False, server_default=text("0"))
    depends_on_filter_key = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("path_id", "filter_key", name="uq_exam_path_filter_schema_path_filter"),
        Index("idx_exam_path_filter_schema_order", "path_id", "sort_order"),
    )


class ExamPathOptionMap(Base):
    __tablename__ = "exam_path_option_map"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_path_catalog.path_id", ondelete="CASCADE"),
        nullable=False
    )

    exam_code = Column(String(32), nullable=False)
    course_type_value = Column(String(64), nullable=True)
    option_label = Column(String(128), nullable=True)

    active = Column(Boolean, nullable=False, server_default=text("true"))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_exam_path_option_map_path_exam", "path_id", "exam_code"),
        Index("idx_exam_path_option_map_active", "path_id", "active"),
    )


class ExamProgramServingMap(Base):
    __tablename__ = "exam_program_serving_map"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_path_catalog.path_id", ondelete="CASCADE"),
        nullable=False
    )

    branch_option_key = Column(String(255), nullable=False)
    branch_label = Column(String(255), nullable=False)

    # New additive discipline -> specialization serving fields
    branch_discipline_key = Column(String(255), nullable=True)
    branch_discipline_label = Column(String(255), nullable=True)
    specialization_key = Column(String(255), nullable=True)
    specialization_label = Column(String(255), nullable=True)
    has_specialization_dimension = Column(Boolean, nullable=False, server_default=text("false"))

    program_code = Column(String(64), nullable=False)
    program_name = Column(Text, nullable=True)

    mapping_confidence = Column(Numeric(5, 4), nullable=True)
    mapping_status = Column(
        SqEnum(MappingStatusEnum, name="mapping_status_enum"),
        nullable=False,
        server_default=MappingStatusEnum.PENDING_REVIEW.value
    )

    approved_by = Column(String(128), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "path_id",
            "branch_option_key",
            "program_code",
            name="uq_exam_program_serving_map_path_branch_program"
        ),
        Index("idx_exam_program_serving_map_branch", "path_id", "branch_option_key"),
        Index("idx_exam_program_serving_map_program", "path_id", "program_code"),
        Index("idx_exam_program_serving_map_status", "path_id", "mapping_status"),
        # New additive lookup indexes for discipline / specialization serving
        Index("idx_exam_program_serving_map_discipline", "path_id", "branch_discipline_key"),
        Index("idx_exam_program_serving_map_specialization", "path_id", "branch_discipline_key", "specialization_key"),
    )


class ExamSeatFilterServingMap(Base):
    __tablename__ = "exam_seat_filter_serving_map"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_path_catalog.path_id", ondelete="CASCADE"),
        nullable=False
    )

    filter_key = Column(String(64), nullable=False)
    option_key = Column(String(128), nullable=False)
    option_label = Column(String(255), nullable=False)

    category_name = Column(String(64), nullable=True)
    is_reserved = Column(Boolean, nullable=True)
    course_type = Column(String(64), nullable=True)
    location_type = Column(String(32), nullable=True)
    reservation_type = Column(String(64), nullable=True)
    seat_bucket_code = Column(String(128), nullable=True)

    display_meta = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    active = Column(Boolean, nullable=False, server_default=text("true"))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "path_id",
            "filter_key",
            "option_key",
            "seat_bucket_code",
            name="uq_exam_seat_filter_serving_map_scope"
        ),
        Index("idx_exam_seat_filter_serving_map_lookup", "path_id", "filter_key", "option_key"),
        Index("idx_exam_seat_filter_serving_map_bucket", "path_id", "seat_bucket_code"),
    )


class ProbabilityPolicyConfig(Base):
    __tablename__ = "probability_policy_config"

    policy_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_key = Column(String(64), nullable=False)

    path_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_path_catalog.path_id", ondelete="CASCADE"),
        nullable=True
    )

    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    version_no = Column(Integer, nullable=False, server_default=text("1"))

    weight_round_evidence = Column(Numeric(6, 4), nullable=False)
    weight_round_stability = Column(Numeric(6, 4), nullable=False)
    weight_current_year_presence = Column(Numeric(6, 4), nullable=False)

    weight_margin = Column(Numeric(6, 4), nullable=False)
    weight_confidence = Column(Numeric(6, 4), nullable=False)

    probability_base = Column(Numeric(8, 4), nullable=False)
    probability_multiplier = Column(Numeric(8, 4), nullable=False)
    probability_min = Column(Numeric(8, 4), nullable=False)
    probability_max = Column(Numeric(8, 4), nullable=False)

    safe_min_margin = Column(Numeric(8, 4), nullable=False)
    safe_min_confidence = Column(Numeric(8, 4), nullable=False)

    moderate_min_margin = Column(Numeric(8, 4), nullable=False)
    moderate_min_confidence = Column(Numeric(8, 4), nullable=False)

    hard_min_margin = Column(Numeric(8, 4), nullable=False)
    hard_min_confidence = Column(Numeric(8, 4), nullable=False)

    suggested_min_margin = Column(Numeric(8, 4), nullable=False)
    suggested_min_confidence = Column(Numeric(8, 4), nullable=False)
    suggested_score_penalty = Column(Numeric(8, 4), nullable=False)
    suggested_probability_penalty = Column(Numeric(8, 4), nullable=False)

    cold_start_probability_cap = Column(Numeric(8, 4), nullable=False)
    cold_start_safe_min_margin = Column(Numeric(8, 4), nullable=False)
    cold_start_safe_min_confidence = Column(Numeric(8, 4), nullable=False)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("policy_key", name="uq_probability_policy_config_key"),
        CheckConstraint("version_no > 0", name="ck_probability_policy_version_positive"),
        Index("idx_probability_policy_active", "is_active"),
        Index("idx_probability_policy_path", "path_id", "is_active"),
    )


class RoundProjectionStats(Base):
    __tablename__ = "round_projection_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    path_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_path_catalog.path_id", ondelete="CASCADE"),
        nullable=False
    )

    college_id = Column(
        UUID(as_uuid=True),
        ForeignKey("college_registry.college_id", ondelete="CASCADE"),
        nullable=False
    )

    exam_code = Column(String(32), nullable=False)
    seat_bucket_code = Column(String(128), nullable=False)
    program_code = Column(String(64), nullable=True)
    round_number = Column(Integer, nullable=False)

    same_round_mean = Column(Numeric(14, 4), nullable=True)
    same_round_median = Column(Numeric(14, 4), nullable=True)
    same_round_stddev = Column(Numeric(14, 4), nullable=True)
    same_round_observation_count = Column(Integer, nullable=False, server_default=text("0"))

    relaxation_ratio_from_prev_round = Column(Numeric(10, 6), nullable=True)

    current_year_presence_score = Column(Numeric(6, 4), nullable=False)
    round_evidence_score = Column(Numeric(6, 4), nullable=False)
    round_stability_score = Column(Numeric(6, 4), nullable=False)

    is_cold_start = Column(Boolean, nullable=False, server_default=text("false"))
    source_years = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    built_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "path_id",
            "college_id",
            "seat_bucket_code",
            "program_code",
            "round_number",
            name="uq_round_projection_stats_scope"
        ),
        Index("idx_round_projection_stats_exam_round", "exam_code", "round_number"),
        Index(
            "idx_round_projection_stats_lookup",
            "path_id",
            "college_id",
            "seat_bucket_code",
            "program_code"
        ),
        Index("idx_round_projection_stats_college", "college_id"),
    )


class SearchReadModelBuild(Base):
    __tablename__ = "search_read_model_builds"

    build_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    status = Column(
        SqEnum(SearchBuildStatusEnum, name="search_build_status_enum"),
        nullable=False
    )

    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    trigger_reason = Column(String(64), nullable=False)
    trigger_exam_code = Column(String(32), nullable=True)

    policy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("probability_policy_config.policy_id", ondelete="SET NULL"),
        nullable=True
    )

    source_latest_ingestion_run_id = Column(UUID(as_uuid=True), nullable=True)
    source_watermark_year = Column(Integer, nullable=True)
    source_watermark_round = Column(Integer, nullable=True)

    rows_written = Column(Integer, nullable=False, server_default=text("0"))
    error_message = Column(Text, nullable=True)
    created_by = Column(String(128), nullable=True)

    __table_args__ = (
        Index("idx_search_read_model_builds_status_started", "status", "started_at"),
    )


class SearchReadModel(Base):
    __tablename__ = "search_read_model"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    build_id = Column(
        UUID(as_uuid=True),
        ForeignKey("search_read_model_builds.build_id", ondelete="CASCADE"),
        nullable=False
    )
    path_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_path_catalog.path_id", ondelete="CASCADE"),
        nullable=False
    )

    path_key = Column(String(64), nullable=False)
    exam_code = Column(String(32), nullable=False)

    live_round_number = Column(Integer, nullable=False)
    comparison_year = Column(Integer, nullable=False)
    comparison_round_number = Column(Integer, nullable=False)

    college_id = Column(UUID(as_uuid=True), ForeignKey("college_registry.college_id", ondelete="CASCADE"), nullable=False)
    college_name = Column(Text, nullable=False)

    institute_code = Column(String(64), nullable=False)
    institute_name = Column(Text, nullable=False)

    program_code = Column(String(64), nullable=False)
    program_name = Column(Text, nullable=False)

    branch_option_key = Column(String(255), nullable=True)

    seat_bucket_code = Column(String(128), nullable=False)
    category_name = Column(String(64), nullable=True)
    reservation_type = Column(String(64), nullable=True)
    location_type = Column(String(32), nullable=True)
    course_type = Column(String(64), nullable=True)

    state_code = Column(String(16), nullable=True)
    district = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)

    hero_storage_key = Column(String, nullable=True)
    hero_public_url = Column(Text, nullable=True)

    metric_type = Column(String(32), nullable=False)

    opening_rank = Column(Numeric(14, 4), nullable=True)
    closing_rank = Column(Numeric(14, 4), nullable=True)
    cutoff_percentile = Column(Numeric(8, 4), nullable=True)

    current_round_cutoff_value = Column(Numeric(14, 4), nullable=True)
    is_projected_current_round = Column(Boolean, nullable=False, server_default=text("false"))

    round_evidence_score = Column(Numeric(6, 4), nullable=False)
    round_stability_score = Column(Numeric(6, 4), nullable=False)
    current_year_presence_score = Column(Numeric(6, 4), nullable=False)

    is_cold_start = Column(Boolean, nullable=False, server_default=text("false"))

    source_authority = Column(Text, nullable=True)
    source_document = Column(Text, nullable=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)

    latest_year_available = Column(Integer, nullable=False)
    latest_round_available = Column(Integer, nullable=False)

    active_policy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("probability_policy_config.policy_id", ondelete="SET NULL"),
        nullable=True
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index(
            "idx_search_read_model_primary_filter",
            "path_id",
            "category_name",
            "comparison_year",
            "comparison_round_number"
        ),
        Index(
            "idx_search_read_model_location",
            "path_id",
            "state_code",
            "district"
        ),
        Index(
            "idx_search_read_model_branch",
            "path_id",
            "branch_option_key"
        ),
        Index(
            "idx_search_read_model_bucket",
            "path_id",
            "seat_bucket_code"
        ),
        Index(
            "idx_search_read_model_metric_round",
            "path_id",
            "live_round_number",
            "metric_type"
        ),
        Index(
            "idx_search_read_model_cursor",
            "path_id",
            "comparison_year",
            "comparison_round_number",
            "current_round_cutoff_value",
            "college_id"
        ),
    )

# --- STUDENT AUTH ENUMS ---

class StudentAccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"


class StudentOnboardingStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class StudentAuthProvider(str, enum.Enum):
    GOOGLE = "GOOGLE"
    APPLE = "APPLE"
    FACEBOOK = "FACEBOOK"
    X = "X"


class StudentSessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


# --- STUDENT USER MODEL ---
class StudentUser(Base):
    __tablename__ = "student_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Platform-owned profile (authoritative after onboarding)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    display_name = Column(String(200), nullable=True)

    # Platform-owned avatar SOT (separate from provider avatar metadata)
    profile_image_storage_key = Column(String(512), nullable=True)

    profile_image_version = Column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
    )

    # India-only v1 phone capture (mandatory later at onboarding, unverified)
    phone_number_e164 = Column(String(20), nullable=True, index=True)
    phone_country_code = Column(String(2), nullable=False, server_default=text("'IN'"))
    phone_is_verified = Column(Boolean, nullable=False, server_default=text("false"))

    # Lifecycle / auth state
    account_status = Column(
        SqEnum(StudentAccountStatus, name="student_account_status_enum"),
        nullable=False,
        server_default=text("'ACTIVE'")
    )
    onboarding_status = Column(
        SqEnum(StudentOnboardingStatus, name="student_onboarding_status_enum"),
        nullable=False,
        server_default=text("'PENDING'")
    )

    # Refresh-safe onboarding recovery
    onboarding_last_completed_step = Column(Integer, nullable=True)

    # Security / activity
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    external_identities = relationship(
        "StudentExternalIdentity",
        back_populates="student_user",
        cascade="all, delete-orphan",
    )
    exam_preferences = relationship(
        "StudentExamPreference",
        back_populates="student_user",
        cascade="all, delete-orphan",
    )
    auth_sessions = relationship(
        "StudentAuthSession",
        back_populates="student_user",
        cascade="all, delete-orphan",
    )
    auth_audit_logs = relationship(
        "StudentAuthAuditLog",
        back_populates="student_user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_student_user_account_status", "account_status"),
        Index("idx_student_user_onboarding_status", "onboarding_status"),
        Index("idx_student_user_created_at", "created_at"),
    )


# --- STUDENT EXTERNAL IDENTITY MODEL ---
class StudentExternalIdentity(Base):
    __tablename__ = "student_external_identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("student_users.id", ondelete="CASCADE"),
        nullable=False,
    )

    provider = Column(
        SqEnum(StudentAuthProvider, name="student_auth_provider_enum"),
        nullable=False,
    )
    provider_user_id = Column(String(255), nullable=False)

    # Optional provider metadata only; never platform SOT
    provider_email = Column(String(255), nullable=True)
    provider_email_verified = Column(Boolean, nullable=True)
    provider_avatar_url = Column(Text, nullable=True)

    raw_claims = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    student_user = relationship("StudentUser", back_populates="external_identities")

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_student_external_identity_provider_user",
        ),
        Index("idx_student_external_identity_student_user", "student_user_id"),
        Index("idx_student_external_identity_provider", "provider"),
    )


# --- STUDENT EXAM PREFERENCE CATALOG MODEL ---
class StudentExamPreferenceCatalog(Base):
    __tablename__ = "student_exam_preference_catalog"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    exam_key = Column(String(64), nullable=False)
    visible_label = Column(String(128), nullable=False)

    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, server_default=text("true"))
    display_order = Column(Integer, nullable=False, server_default=text("0"))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    preferences = relationship(
        "StudentExamPreference",
        back_populates="exam_catalog_item",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("exam_key", name="uq_student_exam_preference_catalog_key"),
        Index("idx_student_exam_preference_catalog_active_order", "active", "display_order"),
    )


# --- STUDENT EXAM PREFERENCE MODEL ---
class StudentExamPreference(Base):
    __tablename__ = "student_exam_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    student_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("student_users.id", ondelete="CASCADE"),
        nullable=False,
    )

    exam_preference_catalog_id = Column(
        UUID(as_uuid=True),
        ForeignKey("student_exam_preference_catalog.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    student_user = relationship("StudentUser", back_populates="exam_preferences")
    exam_catalog_item = relationship("StudentExamPreferenceCatalog", back_populates="preferences")

    __table_args__ = (
        UniqueConstraint(
            "student_user_id",
            "exam_preference_catalog_id",
            name="uq_student_exam_preference_user_catalog_item",
        ),
        Index("idx_student_exam_preference_catalog_id", "exam_preference_catalog_id"),
    )


# --- STUDENT AUTH SESSION MODEL ---
class StudentAuthSession(Base):
    __tablename__ = "student_auth_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("student_users.id", ondelete="CASCADE"),
        nullable=False,
    )

    refresh_token_fingerprint = Column(String(128), nullable=False)
    status = Column(
        SqEnum(StudentSessionStatus, name="student_session_status_enum"),
        nullable=False,
        server_default=text("'ACTIVE'")
    )

    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    student_user = relationship("StudentUser", back_populates="auth_sessions")

    __table_args__ = (
        Index("idx_student_auth_session_student_user", "student_user_id"),
        Index("idx_student_auth_session_status", "status"),
        Index("idx_student_auth_session_expires_at", "expires_at"),
    )


# --- STUDENT AUTH AUDIT LOG MODEL ---
class StudentAuthAuditLog(Base):
    __tablename__ = "student_auth_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("student_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    provider = Column(
        SqEnum(StudentAuthProvider, name="student_auth_provider_enum"),
        nullable=True,
    )

    event_type = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)
    details = Column(JSONB, nullable=False, default=dict)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    student_user = relationship("StudentUser", back_populates="auth_audit_logs")

    __table_args__ = (
        Index("idx_student_auth_audit_user_created", "student_user_id", "created_at"),
        Index("idx_student_auth_audit_provider_created", "provider", "created_at"),
    )