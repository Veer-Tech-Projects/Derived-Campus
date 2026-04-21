"""add student auth foundation models

Revision ID: 6edfe99599a3
Revises: a73ab1ec7e71
Create Date: 2026-04-08 15:26:22.777257+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6edfe99599a3'
down_revision: Union[str, None] = 'a73ab1ec7e71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'student_exam_preference_catalog',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('exam_key', sa.String(length=64), nullable=False),
        sa.Column('visible_label', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exam_key', name='uq_student_exam_preference_catalog_key')
    )
    op.create_index(
        'idx_student_exam_preference_catalog_active_order',
        'student_exam_preference_catalog',
        ['active', 'display_order'],
        unique=False
    )

    op.create_table(
        'student_users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('display_name', sa.String(length=200), nullable=True),
        sa.Column('profile_image_storage_key', sa.String(length=512), nullable=True),
        sa.Column('phone_number_e164', sa.String(length=20), nullable=True),
        sa.Column('phone_country_code', sa.String(length=2), server_default=sa.text("'IN'"), nullable=False),
        sa.Column('phone_is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column(
            'account_status',
            sa.Enum('ACTIVE', 'SUSPENDED', 'DISABLED', name='student_account_status_enum'),
            server_default=sa.text("'ACTIVE'"),
            nullable=False
        ),
        sa.Column(
            'onboarding_status',
            sa.Enum('PENDING', 'COMPLETED', name='student_onboarding_status_enum'),
            server_default=sa.text("'PENDING'"),
            nullable=False
        ),
        sa.Column('onboarding_last_completed_step', sa.Integer(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_student_user_account_status', 'student_users', ['account_status'], unique=False)
    op.create_index('idx_student_user_created_at', 'student_users', ['created_at'], unique=False)
    op.create_index('idx_student_user_onboarding_status', 'student_users', ['onboarding_status'], unique=False)
    op.create_index('ix_student_users_phone_number_e164', 'student_users', ['phone_number_e164'], unique=False)

    op.create_table(
        'student_auth_audit_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('student_user_id', sa.UUID(), nullable=True),
        sa.Column(
            'provider',
            sa.Enum('GOOGLE', 'APPLE', 'FACEBOOK', 'X', name='student_auth_provider_enum'),
            nullable=True
        ),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['student_user_id'], ['student_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_student_auth_audit_provider_created', 'student_auth_audit_log', ['provider', 'created_at'], unique=False)
    op.create_index('idx_student_auth_audit_user_created', 'student_auth_audit_log', ['student_user_id', 'created_at'], unique=False)
    op.create_index('ix_student_auth_audit_log_created_at', 'student_auth_audit_log', ['created_at'], unique=False)
    op.create_index('ix_student_auth_audit_log_event_type', 'student_auth_audit_log', ['event_type'], unique=False)
    op.create_index('ix_student_auth_audit_log_status', 'student_auth_audit_log', ['status'], unique=False)

    op.create_table(
        'student_auth_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('student_user_id', sa.UUID(), nullable=False),
        sa.Column('refresh_token_fingerprint', sa.String(length=128), nullable=False),
        sa.Column(
            'status',
            sa.Enum('ACTIVE', 'REVOKED', 'EXPIRED', name='student_session_status_enum'),
            server_default=sa.text("'ACTIVE'"),
            nullable=False
        ),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(['student_user_id'], ['student_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_student_auth_session_expires_at', 'student_auth_sessions', ['expires_at'], unique=False)
    op.create_index('idx_student_auth_session_status', 'student_auth_sessions', ['status'], unique=False)
    op.create_index('idx_student_auth_session_student_user', 'student_auth_sessions', ['student_user_id'], unique=False)

    op.create_table(
        'student_exam_preferences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('student_user_id', sa.UUID(), nullable=False),
        sa.Column('exam_preference_catalog_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['exam_preference_catalog_id'], ['student_exam_preference_catalog.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['student_user_id'], ['student_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_user_id', 'exam_preference_catalog_id', name='uq_student_exam_preference_user_catalog_item')
    )
    op.create_index('idx_student_exam_preference_catalog_id', 'student_exam_preferences', ['exam_preference_catalog_id'], unique=False)

    op.create_table(
        'student_external_identities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('student_user_id', sa.UUID(), nullable=False),
        sa.Column(
            'provider',
            sa.Enum('GOOGLE', 'APPLE', 'FACEBOOK', 'X', name='student_auth_provider_enum'),
            nullable=False
        ),
        sa.Column('provider_user_id', sa.String(length=255), nullable=False),
        sa.Column('provider_email', sa.String(length=255), nullable=True),
        sa.Column('provider_email_verified', sa.Boolean(), nullable=True),
        sa.Column('provider_avatar_url', sa.Text(), nullable=True),
        sa.Column('raw_claims', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['student_user_id'], ['student_users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_student_external_identity_provider_user')
    )
    op.create_index('idx_student_external_identity_provider', 'student_external_identities', ['provider'], unique=False)
    op.create_index('idx_student_external_identity_student_user', 'student_external_identities', ['student_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_student_external_identity_student_user', table_name='student_external_identities')
    op.drop_index('idx_student_external_identity_provider', table_name='student_external_identities')
    op.drop_table('student_external_identities')

    op.drop_index('idx_student_exam_preference_catalog_id', table_name='student_exam_preferences')
    op.drop_table('student_exam_preferences')

    op.drop_index('idx_student_auth_session_student_user', table_name='student_auth_sessions')
    op.drop_index('idx_student_auth_session_status', table_name='student_auth_sessions')
    op.drop_index('idx_student_auth_session_expires_at', table_name='student_auth_sessions')
    op.drop_table('student_auth_sessions')

    op.drop_index('ix_student_auth_audit_log_status', table_name='student_auth_audit_log')
    op.drop_index('ix_student_auth_audit_log_event_type', table_name='student_auth_audit_log')
    op.drop_index('ix_student_auth_audit_log_created_at', table_name='student_auth_audit_log')
    op.drop_index('idx_student_auth_audit_user_created', table_name='student_auth_audit_log')
    op.drop_index('idx_student_auth_audit_provider_created', table_name='student_auth_audit_log')
    op.drop_table('student_auth_audit_log')

    op.drop_index('ix_student_users_phone_number_e164', table_name='student_users')
    op.drop_index('idx_student_user_onboarding_status', table_name='student_users')
    op.drop_index('idx_student_user_created_at', table_name='student_users')
    op.drop_index('idx_student_user_account_status', table_name='student_users')
    op.drop_table('student_users')

    op.drop_index('idx_student_exam_preference_catalog_active_order', table_name='student_exam_preference_catalog')
    op.drop_table('student_exam_preference_catalog')

    op.execute("DROP TYPE IF EXISTS student_session_status_enum")
    op.execute("DROP TYPE IF EXISTS student_auth_provider_enum")
    op.execute("DROP TYPE IF EXISTS student_onboarding_status_enum")
    op.execute("DROP TYPE IF EXISTS student_account_status_enum")