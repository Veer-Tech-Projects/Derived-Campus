"""add_discovery_engine_fields

Revision ID: a9ef6b52310c
Revises: 99a15aa0b2bd
Create Date: 2026-02-13 15:44:30.979052+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9ef6b52310c'
down_revision: Union[str, None] = '99a15aa0b2bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add Columns to ExamConfiguration (Resilience)
    op.add_column('exam_configuration', sa.Column('consecutive_failure_count', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('exam_configuration', sa.Column('is_under_maintenance', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('exam_configuration', sa.Column('last_scan_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Add Columns to DiscoveredArtifact (Integrity)
    op.add_column('discovered_artifacts', sa.Column('content_hash', sa.String(length=64), nullable=True))
    op.add_column('discovered_artifacts', sa.Column('previous_content_hash', sa.String(length=64), nullable=True))
    op.add_column('discovered_artifacts', sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))

    # 3. [CRITICAL] Deterministic Deduplication (The ChatGPT Fix)
    # Keeps ONLY the latest row (by created_at or ID) for each unique identity group.
    op.execute("""
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY exam_code, year, pdf_path
                       ORDER BY created_at DESC, id DESC
                   ) AS rnk
            FROM discovered_artifacts
        )
        DELETE FROM discovered_artifacts
        WHERE id IN (
            SELECT id FROM ranked WHERE rnk > 1
        );
    """)

    # 4. Apply the Unique Constraint
    op.create_unique_constraint('uq_artifact_identity', 'discovered_artifacts', ['exam_code', 'year', 'pdf_path'])


def downgrade() -> None:
    # 1. Remove Constraint
    op.drop_constraint('uq_artifact_identity', 'discovered_artifacts', type_='unique')

    # 2. Remove Artifact Columns
    op.drop_column('discovered_artifacts', 'last_seen_at')
    op.drop_column('discovered_artifacts', 'previous_content_hash')
    op.drop_column('discovered_artifacts', 'content_hash')

    # 3. Remove Configuration Columns
    op.drop_column('exam_configuration', 'last_scan_at')
    op.drop_column('exam_configuration', 'is_under_maintenance')
    op.drop_column('exam_configuration', 'consecutive_failure_count')