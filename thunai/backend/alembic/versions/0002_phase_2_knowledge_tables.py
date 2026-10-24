"""phase 2 knowledge tables: expert tips, documents, alarm codes, embeddings, fault-card review fields.

Existing fault cards get empty defaults for the new columns.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-24 07:44:04.576478
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('embeddings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_type', sa.String(length=20), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('model', sa.String(length=120), nullable=False),
    sa.Column('vector', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('text_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_type', 'source_id', 'model')
    )
    op.create_index(op.f('ix_embeddings_source_id'), 'embeddings', ['source_id'], unique=False)
    op.create_table('documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=True),
    sa.Column('machine_type_id', sa.Integer(), nullable=True),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('file_path', sa.String(length=400), nullable=False),
    sa.Column('mime', sa.String(length=120), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('pages', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('error', sa.Text(), nullable=False),
    sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('uploaded_by', sa.Integer(), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
    sa.ForeignKeyConstraint(['machine_type_id'], ['machine_types.id'], ),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_machine_id'), 'documents', ['machine_id'], unique=False)
    op.create_index(op.f('ix_documents_machine_type_id'), 'documents', ['machine_type_id'], unique=False)
    op.create_table('alarm_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=True),
    sa.Column('machine_type_id', sa.Integer(), nullable=True),
    sa.Column('code', sa.String(length=60), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('cause', sa.Text(), nullable=False),
    sa.Column('remedy', sa.Text(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
    sa.ForeignKeyConstraint(['machine_type_id'], ['machine_types.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alarm_codes_code'), 'alarm_codes', ['code'], unique=False)
    op.create_index(op.f('ix_alarm_codes_machine_id'), 'alarm_codes', ['machine_id'], unique=False)
    op.create_index(op.f('ix_alarm_codes_machine_type_id'), 'alarm_codes', ['machine_type_id'], unique=False)
    op.create_table('document_chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('page', sa.Integer(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)
    op.create_table('expert_tips',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('machine_id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('original', sa.Text(), nullable=False),
    sa.Column('original_lang', sa.String(length=10), nullable=False),
    sa.Column('english', sa.Text(), nullable=False),
    sa.Column('tamil', sa.Text(), nullable=False),
    sa.Column('media_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('reviewed_by', sa.Integer(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reject_reason', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
    sa.ForeignKeyConstraint(['media_id'], ['log_media.id'], ),
    sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expert_tips_machine_id'), 'expert_tips', ['machine_id'], unique=False)
    op.create_index(op.f('ix_expert_tips_status'), 'expert_tips', ['status'], unique=False)
    op.add_column('fault_cards', sa.Column('group_key', sa.String(length=200), nullable=False, server_default=''))
    op.add_column('fault_cards', sa.Column('drafted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('fault_cards', sa.Column('ai_model', sa.String(length=80), nullable=False, server_default=''))
    op.add_column('fault_cards', sa.Column('review_note', sa.Text(), nullable=False, server_default=''))
    op.add_column('fault_cards', sa.Column('flagged_log_ids', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='[]'))
    op.add_column('fault_cards', sa.Column('history', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False, server_default='[]'))
    op.add_column('fault_cards', sa.Column('replaces_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_fault_cards_replaces_id', 'fault_cards', 'fault_cards', ['replaces_id'], ['id'])
    op.create_index(op.f('ix_fault_cards_group_key'), 'fault_cards', ['group_key'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_fault_cards_group_key'), table_name='fault_cards')
    op.drop_constraint('fk_fault_cards_replaces_id', 'fault_cards', type_='foreignkey')
    op.drop_column('fault_cards', 'replaces_id')
    op.drop_column('fault_cards', 'history')
    op.drop_column('fault_cards', 'flagged_log_ids')
    op.drop_column('fault_cards', 'review_note')
    op.drop_column('fault_cards', 'ai_model')
    op.drop_column('fault_cards', 'drafted_at')
    op.drop_column('fault_cards', 'group_key')
    op.drop_index(op.f('ix_expert_tips_status'), table_name='expert_tips')
    op.drop_index(op.f('ix_expert_tips_machine_id'), table_name='expert_tips')
    op.drop_table('expert_tips')
    op.drop_index(op.f('ix_document_chunks_document_id'), table_name='document_chunks')
    op.drop_table('document_chunks')
    op.drop_index(op.f('ix_alarm_codes_machine_type_id'), table_name='alarm_codes')
    op.drop_index(op.f('ix_alarm_codes_machine_id'), table_name='alarm_codes')
    op.drop_index(op.f('ix_alarm_codes_code'), table_name='alarm_codes')
    op.drop_table('alarm_codes')
    op.drop_index(op.f('ix_documents_machine_type_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_machine_id'), table_name='documents')
    op.drop_table('documents')
    op.drop_index(op.f('ix_embeddings_source_id'), table_name='embeddings')
    op.drop_table('embeddings')
