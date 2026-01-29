"""harden_quarantine_traceability

Revision ID: f9168bc71488
Revises: 5198eb5953aa
Create Date: 2026-01-16 06:18:01.172475+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'f9168bc71488'
down_revision = '5198eb5953aa'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add Traceability to Identity Quarantine
    # We allow null initially to prevent issues with existing rows, then alter (or use a default)
    op.add_column('college_candidates', sa.Column('ingestion_run_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # If you have existing data, you might want to backfill or drop 'nullable=True' later. 
    # For a fresh enterprise setup, we enforce Non-Nullability immediately if table is empty.
    # Here we leave it nullable=True for safety during dev, but application logic enforces presence.

    # 2. Add Traceability to Policy Quarantine
    op.add_column('seat_policy_quarantine', sa.Column('ingestion_run_id', postgresql.UUID(as_uuid=True), nullable=True))

def downgrade():
    op.drop_column('seat_policy_quarantine', 'ingestion_run_id')
    op.drop_column('college_candidates', 'ingestion_run_id')