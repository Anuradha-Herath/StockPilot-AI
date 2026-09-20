"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-19 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('ADMIN', 'MANAGER', 'OPERATOR', 'AUDITOR', name='user_role_enum', native_enum=False), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Products
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sku', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False, server_default='unit'),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('unit_price >= 0', name='chk_product_unit_price_positive'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_category'), 'products', ['category'], unique=False)
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=True)
    op.create_index('ix_products_category_name', 'products', ['category', 'name'], unique=False)

    # Suppliers
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('contact_person', sa.String(length=150), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('lead_time_days', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=False, server_default='4.50'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('lead_time_days >= 0', name='chk_supplier_lead_time_non_negative'),
        sa.CheckConstraint('rating >= 1.00 AND rating <= 5.00', name='chk_supplier_rating_range'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_suppliers_code'), 'suppliers', ['code'], unique=True)
    op.create_index(op.f('ix_suppliers_name'), 'suppliers', ['name'], unique=False)

    # Supplier Products
    op.create_table(
        'supplier_products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('supplier_sku', sa.String(length=100), nullable=True),
        sa.Column('unit_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('min_order_qty', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('lead_time_days', sa.Integer(), nullable=True),
        sa.Column('is_preferred', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('unit_cost > 0', name='chk_supplier_product_cost_positive'),
        sa.CheckConstraint('min_order_qty >= 1', name='chk_supplier_product_moq_positive'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('supplier_id', 'product_id', name='uq_supplier_product')
    )
    op.create_index(op.f('ix_supplier_products_product_id'), 'supplier_products', ['product_id'], unique=False)
    op.create_index(op.f('ix_supplier_products_supplier_id'), 'supplier_products', ['supplier_id'], unique=False)

    # Inventory Levels
    op.create_table(
        'inventory_levels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('current_stock', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reserved_stock', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reorder_point', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('reorder_quantity', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('max_stock', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('warehouse_location', sa.String(length=100), nullable=True),
        sa.Column('last_restocked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('current_stock >= 0', name='chk_inventory_current_stock_non_negative'),
        sa.CheckConstraint('reserved_stock >= 0', name='chk_inventory_reserved_stock_non_negative'),
        sa.CheckConstraint('reorder_point >= 0', name='chk_inventory_reorder_point_non_negative'),
        sa.CheckConstraint('reorder_quantity >= 1', name='chk_inventory_reorder_qty_positive'),
        sa.CheckConstraint('max_stock >= reorder_point', name='chk_inventory_max_gte_reorder'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id')
    )

    # Purchase Requests
    op.create_table(
        'purchase_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_number', sa.String(length=50), nullable=False),
        sa.Column('requester_id', sa.Integer(), nullable=True),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'CONVERTED_TO_PO', 'CANCELLED', name='purchase_request_status_enum', native_enum=False), nullable=False),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='priority_level_enum', native_enum=False), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('total_estimated_cost', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('total_estimated_cost >= 0', name='chk_request_total_cost_positive'),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_requests_request_number'), 'purchase_requests', ['request_number'], unique=True)
    op.create_index(op.f('ix_purchase_requests_status'), 'purchase_requests', ['status'], unique=False)

    # Purchase Request Items
    op.create_table(
        'purchase_request_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('purchase_request_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('estimated_unit_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('quantity >= 1', name='chk_request_item_qty_positive'),
        sa.CheckConstraint('estimated_unit_cost >= 0', name='chk_request_item_unit_cost_positive'),
        sa.CheckConstraint('total_cost >= 0', name='chk_request_item_total_cost_positive'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['purchase_request_id'], ['purchase_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Purchase Orders
    op.create_table(
        'purchase_orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('order_number', sa.String(length=50), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'ISSUED', 'PARTIALLY_RECEIVED', 'FULFILLED', 'CANCELLED', name='purchase_order_status_enum', native_enum=False), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('approved_by_id', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expected_delivery_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('total_amount >= 0', name='chk_order_total_amount_positive'),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_orders_order_number'), 'purchase_orders', ['order_number'], unique=True)
    op.create_index(op.f('ix_purchase_orders_status'), 'purchase_orders', ['status'], unique=False)

    # Purchase Order Items
    op.create_table(
        'purchase_order_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('purchase_order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('line_total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('received_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('quantity >= 1', name='chk_order_item_qty_positive'),
        sa.CheckConstraint('unit_cost >= 0', name='chk_order_item_unit_cost_positive'),
        sa.CheckConstraint('line_total >= 0', name='chk_order_item_line_total_positive'),
        sa.CheckConstraint('received_quantity >= 0', name='chk_order_item_received_qty_non_negative'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Approval Records
    op.create_table(
        'approval_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('purchase_request_id', sa.Integer(), nullable=True),
        sa.Column('purchase_order_id', sa.Integer(), nullable=True),
        sa.Column('approver_id', sa.Integer(), nullable=False),
        sa.Column('decision', sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'MODIFIED', name='approval_decision_enum', native_enum=False), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('decision_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['purchase_request_id'], ['purchase_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('actor_type', sa.Enum('AI_AGENT', 'USER', 'SYSTEM', name='actor_type_enum', native_enum=False), nullable=False),
        sa.Column('actor_id', sa.String(length=100), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=True),
        sa.Column('payload_before', sa.JSON(), nullable=True),
        sa.Column('payload_after', sa.JSON(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_action_time', 'audit_logs', ['action', 'timestamp'], unique=False)
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('approval_records')
    op.drop_table('purchase_order_items')
    op.drop_table('purchase_orders')
    op.drop_table('purchase_request_items')
    op.drop_table('purchase_requests')
    op.drop_table('inventory_levels')
    op.drop_table('supplier_products')
    op.drop_table('suppliers')
    op.drop_table('products')
    op.drop_table('users')
