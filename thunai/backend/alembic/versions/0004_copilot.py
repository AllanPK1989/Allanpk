"""microsoft copilot: user accounts, session channel and photo readings, tool-call log.

Removes the PWA photo-reading columns from log_media (the agent reads photos in Teams now).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-25 09:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.create_table('copilot_calls',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('operation', sa.String(length=60), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('status_code', sa.Integer(), nullable=False),
    sa.Column('ok', sa.Boolean(), nullable=False),
    sa.Column('error', sa.String(length=300), nullable=False),
    sa.Column('duration_ms', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_copilot_calls_created_at'), 'copilot_calls', ['created_at'], unique=False)
    op.create_index(op.f('ix_copilot_calls_operation'), 'copilot_calls', ['operation'], unique=False)
    op.create_index(op.f('ix_copilot_calls_user_id'), 'copilot_calls', ['user_id'], unique=False)
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('entra_upn', sa.String(length=200), nullable=True))
        batch.add_column(sa.Column('entra_oid', sa.String(length=64), nullable=True))
        batch.create_unique_constraint('uq_users_entra_upn', ['entra_upn'])
        batch.create_unique_constraint('uq_users_entra_oid', ['entra_oid'])
    op.add_column('ai_sessions', sa.Column('channel', sa.String(length=10), nullable=False, server_default='app'))
    op.add_column('ai_sessions', sa.Column('observations', JSON, nullable=False, server_default='[]'))
    with op.batch_alter_table('log_media') as batch:
        batch.drop_column('observation_model')
        batch.drop_column('observed_at')
        batch.drop_column('observation')


def downgrade() -> None:
    op.add_column('log_media', sa.Column('observation', JSON, nullable=False, server_default='{}'))
    op.add_column('log_media', sa.Column('observed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('log_media', sa.Column('observation_model', sa.String(length=80), nullable=False, server_default=''))
    with op.batch_alter_table('ai_sessions') as batch:
        batch.drop_column('observations')
        batch.drop_column('channel')
    with op.batch_alter_table('users') as batch:
        batch.drop_constraint('uq_users_entra_oid', type_='unique')
        batch.drop_constraint('uq_users_entra_upn', type_='unique')
        batch.drop_column('entra_oid')
        batch.drop_column('entra_upn')
    op.drop_index(op.f('ix_copilot_calls_user_id'), table_name='copilot_calls')
    op.drop_index(op.f('ix_copilot_calls_operation'), table_name='copilot_calls')
    op.drop_index(op.f('ix_copilot_calls_created_at'), table_name='copilot_calls')
    op.drop_table('copilot_calls')
