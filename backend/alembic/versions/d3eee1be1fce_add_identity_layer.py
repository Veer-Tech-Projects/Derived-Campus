"""add_identity_layer

Revision ID: d3eee1be1fce
Revises: abc1e382caff
Create Date: 2026-01-08 17:28:07.387154+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd3eee1be1fce'
down_revision: Union[str, None] = 'abc1e382caff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the NEW tables (Registry, Aliases, Candidates)
    op.create_table('college_candidates',
        sa.Column('candidate_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('raw_name', sa.Text(), nullable=False),
        sa.Column('source_document', sa.Text(), nullable=False),
        sa.Column('reason_flagged', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('candidate_id')
    )
    
    op.create_table('college_registry',
        sa.Column('college_id', sa.UUID(), nullable=False),
        sa.Column('canonical_name', sa.Text(), nullable=False),
        sa.Column('normalized_name', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('official_website', sa.Text(), nullable=True),
        sa.Column('country_code', sa.String(length=2), server_default='IN', nullable=False),
        sa.Column('state_code', sa.String(length=16), nullable=False),
        sa.Column('city', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('college_id'),
        sa.UniqueConstraint('normalized_name')
    )
    
    op.create_table('college_aliases',
        sa.Column('alias_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('college_id', sa.UUID(), nullable=False),
        sa.Column('alias_name', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(length=64), nullable=False),
        sa.Column('is_approved', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['college_id'], ['college_registry.college_id'], ),
        sa.PrimaryKeyConstraint('alias_id')
    )
    
    op.create_index('idx_alias_lookup', 'college_aliases', ['alias_name'], unique=False)

    # 2. ALTER the EXISTING cutoff_outcomes table (Do NOT create it)
    # Add the new college_id column
    op.add_column('cutoff_outcomes', sa.Column('college_id', sa.UUID(), nullable=True))
    
    # Add the Foreign Key linking Fact -> Registry
    op.create_foreign_key(
        'fk_cutoff_college', 
        'cutoff_outcomes', 'college_registry', 
        ['college_id'], ['college_id']
    )
    
    # Add the index for the new column
    op.create_index('idx_cutoff_college_link', 'cutoff_outcomes', ['college_id'], unique=False)


def downgrade() -> None:
    # Reverse order of operations
    op.drop_index('idx_cutoff_college_link', table_name='cutoff_outcomes')
    op.drop_constraint('fk_cutoff_college', 'cutoff_outcomes', type_='foreignkey')
    op.drop_column('cutoff_outcomes', 'college_id')
    
    op.drop_index('idx_alias_lookup', table_name='college_aliases')
    op.drop_table('college_aliases')
    op.drop_table('college_registry')
    op.drop_table('college_candidates')