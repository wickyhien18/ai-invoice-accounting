"""invoice_file_chunks: luu noi dung file hoa don trong CSDL

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21 09:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('invoice_file_chunks',
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('seq', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('content', sa.LargeBinary().with_variant(mysql.MEDIUMBLOB(), 'mysql'), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.invoice_id']),
        sa.PrimaryKeyConstraint('invoice_id', 'seq'),
        mysql_charset='utf8mb4', mysql_collate='utf8mb4_unicode_ci', mysql_engine='InnoDB')


def downgrade() -> None:
    op.drop_table('invoice_file_chunks')
