"""add_policy_quarantine

Revision ID: 5198eb5953aa
Revises: 938e4cf5f82a
Create Date: 2026-01-15 18:06:24.794399+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '5198eb5953aa'
down_revision = '938e4cf5f82a'
branch_labels = None
depends_on = None


def table_exists(table_name):
    bind = op.get_bind()
    inspector = inspect(bind)
    return inspector.has_table(table_name)

def upgrade():
    if not table_exists('seat_policy_quarantine'):
        op.create_table(
            'seat_policy_quarantine',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('exam_code', sa.String(length=32), nullable=False),
            sa.Column('seat_bucket_code', sa.String(length=128), nullable=False),
            sa.Column('violation_type', sa.String(length=64), nullable=False),
            sa.Column('source_exam', sa.String(length=32), nullable=False),
            sa.Column('source_year', sa.Integer(), nullable=False),
            sa.Column('source_round', sa.Integer(), nullable=True),
            sa.Column('source_file', sa.Text(), nullable=True),
            sa.Column('raw_row', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('status', sa.String(length=32), server_default='OPEN', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_policy_quarantine_exam', 'seat_policy_quarantine', ['exam_code'], unique=False)
        op.create_index('idx_policy_quarantine_bucket', 'seat_policy_quarantine', ['seat_bucket_code'], unique=False)
        op.create_index('idx_policy_quarantine_status', 'seat_policy_quarantine', ['status'], unique=False)

def downgrade():
    if table_exists('seat_policy_quarantine'):
        op.drop_index('idx_policy_quarantine_status', table_name='seat_policy_quarantine')
        op.drop_index('idx_policy_quarantine_bucket', table_name='seat_policy_quarantine')
        op.drop_index('idx_policy_quarantine_exam', table_name='seat_policy_quarantine')
        op.drop_table('seat_policy_quarantine')
