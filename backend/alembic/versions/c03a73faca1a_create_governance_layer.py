"""create_governance_layer

Revision ID: c03a73faca1a
Revises: f9168bc71488
Create Date: 2026-01-18 07:56:48.555677+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'c03a73faca1a'
down_revision: Union[str, None] = 'f9168bc71488'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name):
    bind = op.get_bind()
    inspector = inspect(bind)
    return inspector.has_table(table_name)

def upgrade():
    if not table_exists('discovered_artifacts'):
        op.create_table(
            'discovered_artifacts',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('pdf_path', sa.Text(), nullable=False),
            sa.Column('notification_url', sa.Text(), nullable=True),
            sa.Column('year', sa.Integer(), nullable=True),
            sa.Column('round_name', sa.Text(), nullable=True),
            sa.Column('seat_type', sa.String(length=32), nullable=True),
            sa.Column('detection_reason', sa.Text(), nullable=False),
            sa.Column('pattern_classification', sa.String(length=32), nullable=False),
            sa.Column('detected_source', sa.String(length=32), nullable=False),
            sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
            sa.Column('reviewed_by', sa.String(length=64), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('review_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('raw_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('pdf_path', 'notification_url', name='uq_discovered_pdf')
        )
        op.create_index('idx_discovered_status', 'discovered_artifacts', ['status'], unique=False)
        op.create_index('idx_discovered_pattern', 'discovered_artifacts', ['pattern_classification'], unique=False)

def downgrade():
    if table_exists('discovered_artifacts'):
        op.drop_index('idx_discovered_pattern', table_name='discovered_artifacts')
        op.drop_index('idx_discovered_status', table_name='discovered_artifacts')
        op.drop_table('discovered_artifacts')