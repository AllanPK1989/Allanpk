"""phase 3 integration tables: spare parts, PM plan, machine alarms, integration keys, webhooks.

Also adds photo observations to log_media and an external reference to breakdown_logs; existing
rows get empty defaults.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-24 14:48:56.492332
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('spare_parts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('part_no', sa.String(length=80), nullable=False),
    sa.Column('description', sa.String(length=300), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=False),
    sa.Column('stock_qty', sa.Float(), nullable=True),
    sa.Column('min_qty', sa.Float(), nullable=True),
    sa.Column('location', sa.String(length=120), nullable=False),
    sa.Column('alt_part_nos', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('match_keys', sa.String(length=600), nullable=False),
    sa.Column('stock_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('source', sa.String(length=40), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_spare_parts_part_no'), 'spare_parts', ['part_no'], unique=True)
    op.create_table('integration_keys',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('key_hash', sa.String(length=64), nullable=False),
    sa.Column('key_prefix', sa.String(length=12), nullable=False),
    sa.Column('scopes', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key_hash')
    )
    op.create_table('webhooks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('events', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('secret', sa.String(length=120), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('part_fits',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('part_id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=True),
    sa.Column('machine_type_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
    sa.ForeignKeyConstraint(['machine_type_id'], ['machine_types.id'], ),
    sa.ForeignKeyConstraint(['part_id'], ['spare_parts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_part_fits_machine_id'), 'part_fits', ['machine_id'], unique=False)
    op.create_index(op.f('ix_part_fits_machine_type_id'), 'part_fits', ['machine_type_id'], unique=False)
    op.create_index(op.f('ix_part_fits_part_id'), 'part_fits', ['part_id'], unique=False)
    op.create_table('pm_tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=False),
    sa.Column('task_code', sa.String(length=80), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('frequency_days', sa.Integer(), nullable=True),
    sa.Column('last_done_on', sa.Date(), nullable=True),
    sa.Column('next_due_on', sa.Date(), nullable=True),
    sa.Column('source', sa.String(length=40), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('machine_id', 'task_code')
    )
    op.create_index(op.f('ix_pm_tasks_machine_id'), 'pm_tasks', ['machine_id'], unique=False)
    op.create_index(op.f('ix_pm_tasks_next_due_on'), 'pm_tasks', ['next_due_on'], unique=False)
    op.create_table('webhook_deliveries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('webhook_id', sa.Integer(), nullable=False),
    sa.Column('event', sa.String(length=40), nullable=False),
    sa.Column('entity_id', sa.String(length=40), nullable=False),
    sa.Column('payload', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_status', sa.Integer(), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_deliveries_created_at'), 'webhook_deliveries', ['created_at'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_next_attempt_at'), 'webhook_deliveries', ['next_attempt_at'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_status'), 'webhook_deliveries', ['status'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_webhook_id'), 'webhook_deliveries', ['webhook_id'], unique=False)
    op.create_table('machine_alarms',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=60), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('raised_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('cleared_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('source', sa.String(length=80), nullable=False),
    sa.Column('event_id', sa.String(length=120), nullable=True),
    sa.Column('log_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['log_id'], ['breakdown_logs.id'], ),
    sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_id'),
    sa.UniqueConstraint('machine_id', 'code', 'raised_at')
    )
    op.create_index(op.f('ix_machine_alarms_code'), 'machine_alarms', ['code'], unique=False)
    op.create_index(op.f('ix_machine_alarms_log_id'), 'machine_alarms', ['log_id'], unique=False)
    op.create_index(op.f('ix_machine_alarms_machine_id'), 'machine_alarms', ['machine_id'], unique=False)
    op.create_index(op.f('ix_machine_alarms_raised_at'), 'machine_alarms', ['raised_at'], unique=False)
    op.add_column('breakdown_logs', sa.Column('external_ref', sa.String(length=80), nullable=False, server_default=''))
    op.create_index(op.f('ix_breakdown_logs_external_ref'), 'breakdown_logs', ['external_ref'], unique=False)
    op.add_column('log_media', sa.Column('observation', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='{}'))
    op.add_column('log_media', sa.Column('observed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('log_media', sa.Column('observation_model', sa.String(length=80), nullable=False, server_default=''))


def downgrade() -> None:
    op.drop_column('log_media', 'observation_model')
    op.drop_column('log_media', 'observed_at')
    op.drop_column('log_media', 'observation')
    op.drop_index(op.f('ix_breakdown_logs_external_ref'), table_name='breakdown_logs')
    op.drop_column('breakdown_logs', 'external_ref')
    op.drop_index(op.f('ix_machine_alarms_raised_at'), table_name='machine_alarms')
    op.drop_index(op.f('ix_machine_alarms_machine_id'), table_name='machine_alarms')
    op.drop_index(op.f('ix_machine_alarms_log_id'), table_name='machine_alarms')
    op.drop_index(op.f('ix_machine_alarms_code'), table_name='machine_alarms')
    op.drop_table('machine_alarms')
    op.drop_index(op.f('ix_webhook_deliveries_webhook_id'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_status'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_next_attempt_at'), table_name='webhook_deliveries')
    op.drop_index(op.f('ix_webhook_deliveries_created_at'), table_name='webhook_deliveries')
    op.drop_table('webhook_deliveries')
    op.drop_index(op.f('ix_pm_tasks_next_due_on'), table_name='pm_tasks')
    op.drop_index(op.f('ix_pm_tasks_machine_id'), table_name='pm_tasks')
    op.drop_table('pm_tasks')
    op.drop_index(op.f('ix_part_fits_part_id'), table_name='part_fits')
    op.drop_index(op.f('ix_part_fits_machine_type_id'), table_name='part_fits')
    op.drop_index(op.f('ix_part_fits_machine_id'), table_name='part_fits')
    op.drop_table('part_fits')
    op.drop_table('webhooks')
    op.drop_table('integration_keys')
    op.drop_index(op.f('ix_spare_parts_part_no'), table_name='spare_parts')
    op.drop_table('spare_parts')
