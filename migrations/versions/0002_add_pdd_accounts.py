"""add pdd collector accounts and qrcode sessions

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建枚举类型
    pdd_account_status = ENUM(
        'pending', 'active', 'expired', 'error',
        name='pdd_account_status',
        create_type=True
    )
    pdd_account_status.create(op.get_bind())

    pdd_qrcode_status = ENUM(
        'waiting', 'scanned', 'confirmed', 'success', 'failed', 'expired',
        name='pdd_qrcode_status',
        create_type=True
    )
    pdd_qrcode_status.create(op.get_bind())

    # pdd_collector_accounts 表
    op.create_table(
        'pdd_collector_accounts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('account_name', sa.String(64), nullable=False, comment='账号备注名称'),
        sa.Column('phone', sa.String(20), nullable=True, comment='绑定手机号'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('login_status', pdd_account_status, nullable=False, server_default='pending', comment='账号状态'),
        sa.Column('storage_state', JSONB, nullable=True, comment='Playwright storage state (cookies + localStorage)'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True, comment='最后登录时间'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='登录态过期时间'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index('ix_pdd_accounts_user_status', 'pdd_collector_accounts', ['user_id', 'login_status'])
    op.create_index('ix_pdd_accounts_user_created', 'pdd_collector_accounts', ['user_id', 'created_at'])

    # pdd_qrcode_sessions 表
    op.create_table(
        'pdd_qrcode_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('qrcode_token', sa.String(128), nullable=False, unique=True, index=True, comment='二维码唯一标识'),
        sa.Column('qrcode_image_base64', sa.Text(), nullable=True, comment='二维码图片 Base64'),
        sa.Column('qrcode_url', sa.String(512), nullable=True, comment='二维码链接（拼多多官方）'),
        sa.Column('status', pdd_qrcode_status, nullable=False, server_default='waiting', comment='二维码状态'),
        sa.Column('storage_state', JSONB, nullable=True, comment='登录成功后的 storage_state'),
        sa.Column('account_info', JSONB, nullable=True, comment='账号信息（店铺名、ID等）'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, comment='二维码过期时间'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='完成时间'),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('pdd_collector_accounts.id', ondelete='SET NULL'), nullable=True),
    )

    op.create_index('ix_pdd_qrcode_user_status', 'pdd_qrcode_sessions', ['user_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_pdd_qrcode_user_status', 'pdd_qrcode_sessions')
    op.drop_table('pdd_qrcode_sessions')

    op.drop_index('ix_pdd_accounts_user_created', 'pdd_collector_accounts')
    op.drop_index('ix_pdd_accounts_user_status', 'pdd_collector_accounts')
    op.drop_table('pdd_collector_accounts')

    # 删除枚举类型
    ENUM(name='pdd_qrcode_status').drop(op.get_bind(), checkfirst=True)
    ENUM(name='pdd_account_status').drop(op.get_bind(), checkfirst=True)