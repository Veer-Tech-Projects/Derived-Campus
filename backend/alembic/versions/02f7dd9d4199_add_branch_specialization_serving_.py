"""add branch specialization serving columns

Revision ID: 02f7dd9d4199
Revises: b2c999d0484e
Create Date: 2026-03-31 18:42:16.158088+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '02f7dd9d4199'
down_revision: Union[str, None] = 'b2c999d0484e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'exam_program_serving_map',
        sa.Column('branch_discipline_key', sa.String(length=128), nullable=True)
    )
    op.add_column(
        'exam_program_serving_map',
        sa.Column('branch_discipline_label', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'exam_program_serving_map',
        sa.Column('specialization_key', sa.String(length=128), nullable=True)
    )
    op.add_column(
        'exam_program_serving_map',
        sa.Column('specialization_label', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'exam_program_serving_map',
        sa.Column(
            'has_specialization_dimension',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False
        )
    )

    op.create_index(
        'idx_exam_program_serving_map_discipline',
        'exam_program_serving_map',
        ['path_id', 'branch_discipline_key'],
        unique=False
    )
    op.create_index(
        'idx_exam_program_serving_map_specialization',
        'exam_program_serving_map',
        ['path_id', 'branch_discipline_key', 'specialization_key'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        'idx_exam_program_serving_map_specialization',
        table_name='exam_program_serving_map'
    )
    op.drop_index(
        'idx_exam_program_serving_map_discipline',
        table_name='exam_program_serving_map'
    )

    op.drop_column('exam_program_serving_map', 'has_specialization_dimension')
    op.drop_column('exam_program_serving_map', 'specialization_label')
    op.drop_column('exam_program_serving_map', 'specialization_key')
    op.drop_column('exam_program_serving_map', 'branch_discipline_label')
    op.drop_column('exam_program_serving_map', 'branch_discipline_key')