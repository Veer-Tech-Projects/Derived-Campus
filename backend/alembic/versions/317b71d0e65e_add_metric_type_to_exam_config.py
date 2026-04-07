"""add_metric_type_to_exam_config

Revision ID: 317b71d0e65e
Revises: a2eb411f9c0e
Create Date: 2026-03-15 13:55:51.825192+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '317b71d0e65e'
down_revision: Union[str, None] = 'a2eb411f9c0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add the column
    op.add_column('exam_configuration', sa.Column('metric_type', sa.String(length=32), server_default='rank', nullable=False))
    
    # 2. ENTERPRISE FIX: Manually enforce the Check Constraint that autogenerate missed
    op.create_check_constraint(
        'check_valid_metric_type',
        'exam_configuration',
        "metric_type IN ('rank', 'percentile')"
    )


def downgrade() -> None:
    # 1. Drop the constraint first
    op.drop_constraint('check_valid_metric_type', 'exam_configuration', type_='check')
    
    # 2. Drop the column
    op.drop_column('exam_configuration', 'metric_type')