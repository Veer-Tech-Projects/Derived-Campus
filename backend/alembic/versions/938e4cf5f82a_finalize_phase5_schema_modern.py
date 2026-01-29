"""finalize_phase5_schema_modern

Revision ID: <YOUR_NEW_ID>
Revises: <YOUR_PREVIOUS_ID>
Create Date: 2026-01-14 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect  # MODERNIZATION FIX

# revision identifiers, used by Alembic.
revision = '938e4cf5f82a'
down_revision = 'd3eee1be1fce'
branch_labels = None
depends_on = None

def constraint_exists(table_name, constraint_name):
    """
    Enterprise Utility: Checks if a constraint exists before creation.
    Uses SQLAlchemy 2.0 compliant inspection.
    """
    bind = op.get_bind()
    inspector = inspect(bind) # Modern API
    constraints = inspector.get_unique_constraints(table_name)
    return any(c['name'] == constraint_name for c in constraints)

def index_exists(table_name, index_name):
    bind = op.get_bind()
    inspector = inspect(bind) # Modern API
    indexes = inspector.get_indexes(table_name)
    return any(i['name'] == index_name for i in indexes)

def table_exists(table_name):
    bind = op.get_bind()
    inspector = inspect(bind) # Modern API
    return inspector.has_table(table_name)

def upgrade():
    # --- PART 1: IDENTITY LAYER HARDENING ---

    # 1. Safely handle constraints for College Registry
    # Make geography nullable (Zero Fabrication)
    op.alter_column('college_registry', 'state_code',
               existing_type=sa.VARCHAR(length=16),
               nullable=True)
    op.alter_column('college_registry', 'city',
               existing_type=sa.TEXT(),
               nullable=True)

    # 2. Apply Named Constraints safely (Introspection Method)
    if not constraint_exists('college_registry', 'uq_college_normalized_name'):
        op.create_unique_constraint('uq_college_normalized_name', 'college_registry', ['normalized_name'])

    if not constraint_exists('college_aliases', 'uq_college_alias_name'):
        op.create_unique_constraint('uq_college_alias_name', 'college_aliases', ['alias_name'])
    
    # 3. Add Performance Indexes safely
    if not index_exists('college_registry', 'idx_college_normalized'):
        op.create_index('idx_college_normalized', 'college_registry', ['normalized_name'])
        
    if not index_exists('college_aliases', 'idx_alias_approved'):
        op.create_index('idx_alias_approved', 'college_aliases', ['is_approved'])

    # --- PART 2: CONTEXT & TAXONOMY (NEW TABLES) ---

    # 4. Create Universal Taxonomy
    if not table_exists('seat_bucket_taxonomy'):
        op.create_table(
            'seat_bucket_taxonomy',
            sa.Column('seat_bucket_code', sa.String(length=128), nullable=False),
            sa.Column('exam_code', sa.String(length=32), nullable=False),
            sa.Column('category_name', sa.String(length=64), nullable=False),
            sa.Column('is_reserved', sa.Boolean(), nullable=False),
            sa.Column('course_type', sa.String(length=64), nullable=True),
            sa.Column('location_type', sa.String(length=32), nullable=True),
            sa.Column('reservation_type', sa.String(length=64), nullable=True),
            sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('seat_bucket_code')
        )
        op.create_index('idx_taxonomy_exam_category', 'seat_bucket_taxonomy', ['exam_code', 'category_name'], unique=False)
        op.create_index('idx_taxonomy_reserved', 'seat_bucket_taxonomy', ['is_reserved'], unique=False)

    # 5. Create KCET Metadata
    if not table_exists('kcet_college_metadata'):
        op.create_table(
            'kcet_college_metadata',
            sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column('college_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('kea_college_code', sa.String(length=16), nullable=False),
            sa.Column('kea_college_name_raw', sa.Text(), nullable=False),
            sa.Column('course_type', sa.String(length=32), nullable=False),
            sa.Column('year', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['college_id'], ['college_registry.college_id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('college_id', 'course_type', 'year', name='uq_kcet_metadata_identity')
        )
        op.create_index('idx_kcet_code_lookup', 'kcet_college_metadata', ['kea_college_code', 'year'], unique=False)
        op.create_index('idx_kcet_college_id', 'kcet_college_metadata', ['college_id'], unique=False)


def downgrade():
    # Only drop if they exist to prevent errors on partial rolls
    # Note: Strictly speaking, downgrade logic in enterprise scripts is rarely used 
    # without a full backup restore, but here is the correct reverse order.
    
    if table_exists('kcet_college_metadata'):
        op.drop_table('kcet_college_metadata') # Indexes drop automatically with table
    
    if table_exists('seat_bucket_taxonomy'):
        op.drop_table('seat_bucket_taxonomy')
    
    # We do NOT drop constraints on the core identity tables in a downgrade 
    # as that could expose data integrity issues.
    pass