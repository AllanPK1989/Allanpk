"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-10-24 04:18:25.792647
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('glossary',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('term_en', sa.String(length=200), nullable=False),
    sa.Column('term_ta', sa.String(length=200), nullable=False),
    sa.Column('spoken_variants', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('category', sa.String(length=60), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_glossary_term_en'), 'glossary', ['term_en'], unique=False)
    op.create_table('machine_types',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('translation_cache',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('target_lang', sa.String(length=2), nullable=False),
    sa.Column('source_text', sa.Text(), nullable=False),
    sa.Column('translated', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('employee_id', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('zone', sa.String(length=80), nullable=False),
    sa.Column('preferred_language', sa.String(length=2), nullable=False),
    sa.Column('skill_level', sa.String(length=40), nullable=False),
    sa.Column('phone', sa.String(length=30), nullable=False),
    sa.Column('pin_hash', sa.String(length=200), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('failed_attempts', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_employee_id'), 'users', ['employee_id'], unique=True)
    op.create_table('audit_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('entity', sa.String(length=40), nullable=False),
    sa.Column('entity_id', sa.String(length=40), nullable=False),
    sa.Column('action', sa.String(length=40), nullable=False),
    sa.Column('before', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('after', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_at'), 'audit_log', ['at'], unique=False)
    op.create_index(op.f('ix_audit_log_entity'), 'audit_log', ['entity'], unique=False)
    op.create_index(op.f('ix_audit_log_entity_id'), 'audit_log', ['entity_id'], unique=False)
    op.create_index(op.f('ix_audit_log_user_id'), 'audit_log', ['user_id'], unique=False)
    op.create_table('machines',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_no', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('machine_type_id', sa.Integer(), nullable=True),
    sa.Column('zone', sa.String(length=80), nullable=False),
    sa.Column('line', sa.String(length=80), nullable=False),
    sa.Column('make', sa.String(length=120), nullable=False),
    sa.Column('model', sa.String(length=120), nullable=False),
    sa.Column('plc_model', sa.String(length=120), nullable=False),
    sa.Column('key_components', sa.Text(), nullable=False),
    sa.Column('criticality', sa.String(length=1), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('qr_code', sa.String(length=300), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['machine_type_id'], ['machine_types.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_machines_machine_no'), 'machines', ['machine_no'], unique=True)
    op.create_index(op.f('ix_machines_zone'), 'machines', ['zone'], unique=False)
    op.create_table('settings',
    sa.Column('key', sa.String(length=80), nullable=False),
    sa.Column('value', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('updated_by', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_table('ai_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=False),
    sa.Column('technician_id', sa.Integer(), nullable=False),
    sa.Column('language', sa.String(length=2), nullable=False),
    sa.Column('problem_text', sa.Text(), nullable=False),
    sa.Column('alarm_code', sa.String(length=60), nullable=False),
    sa.Column('questions_and_answers', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('steps', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('step_responses', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('sources_used', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('procedure_meta', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('model', sa.String(length=80), nullable=False),
    sa.Column('prompt_version', sa.String(length=40), nullable=False),
    sa.Column('input_tokens', sa.Integer(), nullable=False),
    sa.Column('output_tokens', sa.Integer(), nullable=False),
    sa.Column('cost_usd', sa.Float(), nullable=False),
    sa.Column('outcome', sa.String(length=20), nullable=False),
    sa.Column('feedback', sa.String(length=20), nullable=False),
    sa.Column('feedback_note', sa.Text(), nullable=False),
    sa.Column('resulting_log_id', sa.Integer(), nullable=True),
    sa.Column('supervisor_called', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
    sa.ForeignKeyConstraint(['technician_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_sessions_machine_id'), 'ai_sessions', ['machine_id'], unique=False)
    op.create_index(op.f('ix_ai_sessions_outcome'), 'ai_sessions', ['outcome'], unique=False)
    op.create_index(op.f('ix_ai_sessions_resulting_log_id'), 'ai_sessions', ['resulting_log_id'], unique=False)
    op.create_index(op.f('ix_ai_sessions_technician_id'), 'ai_sessions', ['technician_id'], unique=False)
    op.create_table('components',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('category', sa.String(length=20), nullable=False),
    sa.Column('part_no', sa.String(length=80), nullable=False),
    sa.Column('make', sa.String(length=120), nullable=False),
    sa.Column('location', sa.String(length=200), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_components_machine_id'), 'components', ['machine_id'], unique=False)
    op.create_table('fault_cards',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=True),
    sa.Column('machine_type_id', sa.Integer(), nullable=True),
    sa.Column('symptom', sa.Text(), nullable=False),
    sa.Column('symptom_ta', sa.Text(), nullable=False),
    sa.Column('causes', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('steps_en', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('steps_ta', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('parts', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('tools', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('avg_fix_min', sa.Integer(), nullable=True),
    sa.Column('source_log_ids', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('approved_by', sa.Integer(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
    sa.ForeignKeyConstraint(['machine_type_id'], ['machine_types.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fault_cards_machine_id'), 'fault_cards', ['machine_id'], unique=False)
    op.create_index(op.f('ix_fault_cards_machine_type_id'), 'fault_cards', ['machine_type_id'], unique=False)
    op.create_index(op.f('ix_fault_cards_status'), 'fault_cards', ['status'], unique=False)
    op.create_table('breakdown_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('log_no', sa.String(length=30), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=False),
    sa.Column('technician_id', sa.Integer(), nullable=True),
    sa.Column('technician_name', sa.String(length=120), nullable=False),
    sa.Column('zone', sa.String(length=80), nullable=False),
    sa.Column('shift', sa.String(length=10), nullable=False),
    sa.Column('shift_date', sa.Date(), nullable=True),
    sa.Column('reported_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('start_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('end_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('downtime_min', sa.Integer(), nullable=True),
    sa.Column('alarm_code', sa.String(length=60), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('verified_by', sa.Integer(), nullable=True),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reject_reason', sa.Text(), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('ai_session_id', sa.Integer(), nullable=True),
    sa.Column('escalated', sa.Boolean(), nullable=False),
    sa.Column('needs_confirmation', sa.Boolean(), nullable=False),
    sa.Column('client_uuid', sa.String(length=64), nullable=True),
    sa.Column('original_language', sa.String(length=10), nullable=False),
    sa.Column('enriched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['ai_session_id'], ['ai_sessions.id'], ),
    sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
    sa.ForeignKeyConstraint(['technician_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_uuid')
    )
    op.create_index(op.f('ix_breakdown_logs_log_no'), 'breakdown_logs', ['log_no'], unique=True)
    op.create_index(op.f('ix_breakdown_logs_machine_id'), 'breakdown_logs', ['machine_id'], unique=False)
    op.create_index(op.f('ix_breakdown_logs_shift_date'), 'breakdown_logs', ['shift_date'], unique=False)
    op.create_index(op.f('ix_breakdown_logs_status'), 'breakdown_logs', ['status'], unique=False)
    op.create_index(op.f('ix_breakdown_logs_technician_id'), 'breakdown_logs', ['technician_id'], unique=False)
    op.create_table('ai_calls',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('purpose', sa.String(length=40), nullable=False),
    sa.Column('provider', sa.String(length=20), nullable=False),
    sa.Column('model', sa.String(length=80), nullable=False),
    sa.Column('prompt_version', sa.String(length=40), nullable=False),
    sa.Column('input_tokens', sa.Integer(), nullable=False),
    sa.Column('output_tokens', sa.Integer(), nullable=False),
    sa.Column('cache_read_tokens', sa.Integer(), nullable=False),
    sa.Column('cache_write_tokens', sa.Integer(), nullable=False),
    sa.Column('cost_usd', sa.Float(), nullable=False),
    sa.Column('ok', sa.Boolean(), nullable=False),
    sa.Column('error', sa.Text(), nullable=False),
    sa.Column('duration_ms', sa.Integer(), nullable=False),
    sa.Column('ai_session_id', sa.Integer(), nullable=True),
    sa.Column('log_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['ai_session_id'], ['ai_sessions.id'], ),
    sa.ForeignKeyConstraint(['log_id'], ['breakdown_logs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_calls_created_at'), 'ai_calls', ['created_at'], unique=False)
    op.create_index(op.f('ix_ai_calls_purpose'), 'ai_calls', ['purpose'], unique=False)
    op.create_table('log_classification',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('log_id', sa.Integer(), nullable=False),
    sa.Column('symptom_category', sa.String(length=120), nullable=False),
    sa.Column('component_id', sa.Integer(), nullable=True),
    sa.Column('component_name', sa.String(length=200), nullable=False),
    sa.Column('failure_mode', sa.String(length=200), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('edited_by', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['component_id'], ['components.id'], ),
    sa.ForeignKeyConstraint(['edited_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['log_id'], ['breakdown_logs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('log_id')
    )
    op.create_table('log_media',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('log_id', sa.Integer(), nullable=True),
    sa.Column('ai_session_id', sa.Integer(), nullable=True),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('file_path', sa.String(length=400), nullable=False),
    sa.Column('mime', sa.String(length=80), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('transcript', sa.Text(), nullable=False),
    sa.Column('stt_provider', sa.String(length=40), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('purged_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['ai_session_id'], ['ai_sessions.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['log_id'], ['breakdown_logs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_log_media_ai_session_id'), 'log_media', ['ai_session_id'], unique=False)
    op.create_index(op.f('ix_log_media_expires_at'), 'log_media', ['expires_at'], unique=False)
    op.create_index(op.f('ix_log_media_log_id'), 'log_media', ['log_id'], unique=False)
    op.create_table('log_parts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('log_id', sa.Integer(), nullable=False),
    sa.Column('part_no', sa.String(length=80), nullable=False),
    sa.Column('description', sa.String(length=300), nullable=False),
    sa.Column('qty', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['log_id'], ['breakdown_logs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_log_parts_log_id'), 'log_parts', ['log_id'], unique=False)
    op.create_table('log_texts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('log_id', sa.Integer(), nullable=False),
    sa.Column('field', sa.String(length=30), nullable=False),
    sa.Column('original', sa.Text(), nullable=False),
    sa.Column('original_lang', sa.String(length=10), nullable=False),
    sa.Column('english', sa.Text(), nullable=False),
    sa.Column('tamil', sa.Text(), nullable=False),
    sa.Column('ai_filled', sa.Boolean(), nullable=False),
    sa.Column('ai_unsure', sa.Boolean(), nullable=False),
    sa.Column('translated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['log_id'], ['breakdown_logs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('log_id', 'field')
    )
    op.create_index(op.f('ix_log_texts_log_id'), 'log_texts', ['log_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_log_texts_log_id'), table_name='log_texts')
    op.drop_table('log_texts')
    op.drop_index(op.f('ix_log_parts_log_id'), table_name='log_parts')
    op.drop_table('log_parts')
    op.drop_index(op.f('ix_log_media_log_id'), table_name='log_media')
    op.drop_index(op.f('ix_log_media_expires_at'), table_name='log_media')
    op.drop_index(op.f('ix_log_media_ai_session_id'), table_name='log_media')
    op.drop_table('log_media')
    op.drop_table('log_classification')
    op.drop_index(op.f('ix_ai_calls_purpose'), table_name='ai_calls')
    op.drop_index(op.f('ix_ai_calls_created_at'), table_name='ai_calls')
    op.drop_table('ai_calls')
    op.drop_index(op.f('ix_breakdown_logs_technician_id'), table_name='breakdown_logs')
    op.drop_index(op.f('ix_breakdown_logs_status'), table_name='breakdown_logs')
    op.drop_index(op.f('ix_breakdown_logs_shift_date'), table_name='breakdown_logs')
    op.drop_index(op.f('ix_breakdown_logs_machine_id'), table_name='breakdown_logs')
    op.drop_index(op.f('ix_breakdown_logs_log_no'), table_name='breakdown_logs')
    op.drop_table('breakdown_logs')
    op.drop_index(op.f('ix_fault_cards_status'), table_name='fault_cards')
    op.drop_index(op.f('ix_fault_cards_machine_type_id'), table_name='fault_cards')
    op.drop_index(op.f('ix_fault_cards_machine_id'), table_name='fault_cards')
    op.drop_table('fault_cards')
    op.drop_index(op.f('ix_components_machine_id'), table_name='components')
    op.drop_table('components')
    op.drop_index(op.f('ix_ai_sessions_technician_id'), table_name='ai_sessions')
    op.drop_index(op.f('ix_ai_sessions_resulting_log_id'), table_name='ai_sessions')
    op.drop_index(op.f('ix_ai_sessions_outcome'), table_name='ai_sessions')
    op.drop_index(op.f('ix_ai_sessions_machine_id'), table_name='ai_sessions')
    op.drop_table('ai_sessions')
    op.drop_table('settings')
    op.drop_index(op.f('ix_machines_zone'), table_name='machines')
    op.drop_index(op.f('ix_machines_machine_no'), table_name='machines')
    op.drop_table('machines')
    op.drop_index(op.f('ix_audit_log_user_id'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_entity_id'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_entity'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_at'), table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_index(op.f('ix_users_employee_id'), table_name='users')
    op.drop_table('users')
    op.drop_table('translation_cache')
    op.drop_table('machine_types')
    op.drop_index(op.f('ix_glossary_term_en'), table_name='glossary')
    op.drop_table('glossary')
