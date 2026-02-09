"""Phase 8 Governance Tables (Final Corrected)

Revision ID: 34fb93569ff2
Revises: 55a25fe2c51f
Create Date: 2026-02-01 16:06:53.027212+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '34fb93569ff2'
down_revision: Union[str, None] = '55a25fe2c51f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Exam Configuration (Master Switch) ---
    op.create_table('exam_configuration',
        sa.Column('exam_code', sa.String(length=32), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('ingestion_mode', sa.String(length=32), server_default='CONTINUOUS', nullable=False),
        sa.Column('config_overrides', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        
        # [AUDIT FIX] Domain Constraint
        sa.CheckConstraint("ingestion_mode IN ('BOOTSTRAP', 'CONTINUOUS')", name='ck_exam_ingestion_mode'),
        sa.PrimaryKeyConstraint('exam_code')
    )

    # --- 2. Registry Audit Log (Compliance) ---
    op.create_table('registry_audit_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('entity_type', sa.String(length=32), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('performed_by', sa.String(length=128), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    # [PERFORMANCE] Indexes for Audit Filtering
    op.create_index('idx_audit_timestamp', 'registry_audit_log', ['timestamp'], unique=False)
    op.create_index('idx_audit_entity', 'registry_audit_log', ['entity_id'], unique=False)
    op.create_index('idx_audit_user', 'registry_audit_log', ['performed_by'], unique=False)

    # --- 3. Ingestion Runs (Flight Recorder) ---
    op.create_table('ingestion_runs',
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('artifact_id', sa.UUID(), nullable=False),
        sa.Column('exam_code', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        
        # [AUDIT FIX] Status Constraint
        sa.CheckConstraint("status IN ('RUNNING', 'COMPLETED', 'FAILED')", name='ck_ingestion_runs_status'),
        sa.ForeignKeyConstraint(['artifact_id'], ['discovered_artifacts.id'], ),
        sa.PrimaryKeyConstraint('run_id')
    )
    # [PERFORMANCE] Indexes for Dashboard Stats
    op.create_index('idx_runs_exam', 'ingestion_runs', ['exam_code'], unique=False)
    op.create_index('idx_runs_status', 'ingestion_runs', ['status'], unique=False)
    op.create_index('idx_runs_artifact', 'ingestion_runs', ['artifact_id'], unique=False)


def downgrade() -> None:
    # --- Reverse Order ---
    op.drop_index('idx_runs_artifact', table_name='ingestion_runs')
    op.drop_index('idx_runs_status', table_name='ingestion_runs')
    op.drop_index('idx_runs_exam', table_name='ingestion_runs')
    op.drop_table('ingestion_runs')
    
    op.drop_index('idx_audit_user', table_name='registry_audit_log')
    op.drop_index('idx_audit_entity', table_name='registry_audit_log')
    op.drop_index('idx_audit_timestamp', table_name='registry_audit_log')
    op.drop_table('registry_audit_log')
    
    op.drop_table('exam_configuration')