"""add_filter_indices

Revision ID: a2eb411f9c0e
Revises: 4f363064b6f5
Create Date: 2026-03-13 11:09:56.191606+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a2eb411f9c0e'
down_revision: Union[str, None] = '4f363064b6f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Standard, instant index creation for small/medium tables
    op.create_index('idx_cutoff_filter', 'cutoff_outcomes', ['exam_code', 'seat_bucket_code', 'program_code', 'year', 'round_number', 'college_id'], unique=False)
    op.create_index('idx_bucket_filter', 'seat_bucket_taxonomy', ['exam_code', 'reservation_type', 'category_name', 'location_type'], unique=False)

def downgrade() -> None:
    op.drop_index('idx_bucket_filter', table_name='seat_bucket_taxonomy')
    op.drop_index('idx_cutoff_filter', table_name='cutoff_outcomes')