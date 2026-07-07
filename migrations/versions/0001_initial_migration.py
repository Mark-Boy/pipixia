"""empty message

Revision ID: 0001
Revises: 
Create Date: 2026-07-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users 表
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), server_default='operator'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # shops 表
    op.create_table(
        'shops',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('shop_name', sa.String(100), nullable=False),
        sa.Column('platform', sa.String(20), server_default='shopee_th'),
        sa.Column('shop_token_encrypted', sa.String(500), nullable=False),
        sa.Column('shop_id', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('config', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # products 表
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('shop_id', sa.Integer(), sa.ForeignKey('shops.id'), nullable=False, index=True),
        sa.Column('source_platform', sa.String(20), nullable=False),
        sa.Column('source_item_id', sa.String(100), nullable=False),
        sa.Column('title_zh', sa.String(255), nullable=False),
        sa.Column('title_th', sa.String(500), nullable=True),
        sa.Column('description_zh', sa.String(5000), nullable=True),
        sa.Column('description_th', sa.String(5000), nullable=True),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('images_oss_keys', sa.JSON(), server_default='[]'),
        sa.Column('price_cny', sa.Float(), nullable=False),
        sa.Column('price_thb', sa.Float(), nullable=False),
        sa.Column('cost_cny', sa.Float(), nullable=False),
        sa.Column('profit_margin', sa.Float(), nullable=True),
        sa.Column('risk_status', sa.String(20), server_default='pending'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # listings 表
    op.create_table(
        'listings',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('shop_id', sa.Integer(), sa.ForeignKey('shops.id'), nullable=False, index=True),
        sa.Column('shopee_item_id', sa.String(50), nullable=True),
        sa.Column('shopee_status', sa.String(20), nullable=True),
        sa.Column('listing_price_thb', sa.Float(), nullable=True),
        sa.Column('stock', sa.Integer(), nullable=True),
        sa.Column('variation_data', sa.JSON(), server_default='{}'),
        sa.Column('audit_status', sa.String(20), server_default='pending'),
        sa.Column('audit_comment', sa.String(500), nullable=True),
        sa.Column('listing_mode', sa.String(20), server_default='manual'),
        sa.Column('retry_count', sa.Integer(), server_default='0'),
        sa.Column('last_error', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # translates 表
    op.create_table(
        'translates',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('translate_type', sa.String(20), nullable=False),
        sa.Column('source_text_hash', sa.String(64), nullable=False, index=True),
        sa.Column('source_text', sa.String(5000), nullable=False),
        sa.Column('target_text', sa.String(5000), nullable=True),
        sa.Column('source_image_url', sa.String(500), nullable=True),
        sa.Column('target_image_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # risk_logs 表
    op.create_table(
        'risk_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('risk_type', sa.String(20), nullable=False),
        sa.Column('risk_detail', sa.String(500), nullable=False),
        sa.Column('action_taken', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # profit_calibration 表
    op.create_table(
        'profit_calibration',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('shop_id', sa.Integer(), sa.ForeignKey('shops.id'), nullable=False, index=True),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('estimated_profit', sa.Float(), nullable=False),
        sa.Column('actual_profit', sa.Float(), nullable=True),
        sa.Column('deviation', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 创建复合索引
    op.create_index('idx_products_shop_status', 'products', ['shop_id', 'status'])
    op.create_index('idx_products_risk', 'products', ['risk_status'])
    op.create_index('idx_listings_product', 'listings', ['product_id'])
    op.create_index('idx_listings_shop', 'listings', ['shop_id'])
    op.create_index('idx_risk_logs_product', 'risk_logs', ['product_id'])
    op.create_index('idx_translates_product', 'translates', ['product_id'])
    op.create_index('idx_profit_calibration_shop', 'profit_calibration', ['shop_id'])


def downgrade() -> None:
    op.drop_index('idx_profit_calibration_shop', 'profit_calibration')
    op.drop_index('idx_translates_product', 'translates')
    op.drop_index('idx_risk_logs_product', 'risk_logs')
    op.drop_index('idx_listings_shop', 'listings')
    op.drop_index('idx_listings_product', 'listings')
    op.drop_index('idx_products_risk', 'products')
    op.drop_index('idx_products_shop_status', 'products')

    op.drop_table('profit_calibration')
    op.drop_table('risk_logs')
    op.drop_table('translates')
    op.drop_table('listings')
    op.drop_table('products')
    op.drop_table('shops')
    op.drop_table('users')
