"""add college_id to round_projection_stats

Revision ID: b2c999d0484e
Revises: 58691c771edc
Create Date: 2026-03-26 07:05:10.495057+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c999d0484e'
down_revision: Union[str, None] = '58691c771edc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nullable first so existing rows do not break migration
    op.add_column(
        'round_projection_stats',
        sa.Column('college_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # 2. This is a derived builder table; clear old invalid rows safely
    op.execute("DELETE FROM round_projection_stats")

    # 3. Make the new column required
    op.alter_column('round_projection_stats', 'college_id', nullable=False)

    # 4. Replace indexes/constraints
    op.drop_index('idx_round_projection_stats_lookup', table_name='round_projection_stats')
    op.create_index(
        'idx_round_projection_stats_lookup',
        'round_projection_stats',
        ['path_id', 'college_id', 'seat_bucket_code', 'program_code'],
        unique=False
    )

    op.drop_constraint('uq_round_projection_stats_scope', 'round_projection_stats', type_='unique')
    op.create_unique_constraint(
        'uq_round_projection_stats_scope',
        'round_projection_stats',
        ['path_id', 'college_id', 'seat_bucket_code', 'program_code', 'round_number']
    )

    op.create_index(
        'idx_round_projection_stats_college',
        'round_projection_stats',
        ['college_id'],
        unique=False
    )

    op.create_foreign_key(
        'fk_round_projection_stats_college_id',
        'round_projection_stats',
        'college_registry',
        ['college_id'],
        ['college_id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint('fk_round_projection_stats_college_id', 'round_projection_stats', type_='foreignkey')
    op.drop_index('idx_round_projection_stats_college', table_name='round_projection_stats')

    op.drop_constraint('uq_round_projection_stats_scope', 'round_projection_stats', type_='unique')
    op.create_unique_constraint(
        'uq_round_projection_stats_scope',
        'round_projection_stats',
        ['path_id', 'seat_bucket_code', 'program_code', 'round_number']
    )

    op.drop_index('idx_round_projection_stats_lookup', table_name='round_projection_stats')
    op.create_index(
        'idx_round_projection_stats_lookup',
        'round_projection_stats',
        ['path_id', 'seat_bucket_code', 'program_code'],
        unique=False
    )

    op.drop_column('round_projection_stats', 'college_id')