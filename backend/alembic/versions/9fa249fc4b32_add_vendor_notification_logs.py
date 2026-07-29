"""add vendor notification logs (alert emails)

Revision ID: 9fa249fc4b32
Revises: 888ff8141fd1
Create Date: 2026-07-23 00:00:00.000000

Adds `vendor_notification_logs`, which records every alert email sent (or
attempted) to a vendor — used both as an audit trail and to dedupe repeat
notifications (a vendor is only re-emailed when their alert moves into a
new urgency tier, not on every daily scheduler run).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9fa249fc4b32'
down_revision: Union[str, None] = '888ff8141fd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

notification_channel_enum = sa.Enum('EMAIL', name='notificationchannel')
notification_trigger_enum = sa.Enum('SCHEDULED', 'MANUAL', name='notificationtrigger')


def upgrade() -> None:
    bind = op.get_bind()
    notification_channel_enum.create(bind, checkfirst=True)
    notification_trigger_enum.create(bind, checkfirst=True)

    op.create_table(
        'vendor_notification_logs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('vendor_id', sa.String(length=36), sa.ForeignKey('vendors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', notification_channel_enum, nullable=False, server_default='EMAIL'),
        sa.Column('trigger', notification_trigger_enum, nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('coverage_type', sa.String(length=50), nullable=True),
        sa.Column('expiry_date', sa.String(length=20), nullable=True),
        sa.Column('urgency_bucket', sa.String(length=20), nullable=False),
        sa.Column('recipient_email', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        op.f('ix_vendor_notification_logs_vendor_id'),
        'vendor_notification_logs', ['vendor_id'], unique=False,
    )
    op.create_index(
        op.f('ix_vendor_notification_logs_trigger'),
        'vendor_notification_logs', ['trigger'], unique=False,
    )
    # Dedupe-lookup index — matches the WHERE clause in
    # NotificationService._already_notified().
    op.create_index(
        'ix_vnl_dedupe_lookup',
        'vendor_notification_logs',
        ['vendor_id', 'alert_type', 'coverage_type', 'expiry_date', 'urgency_bucket'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_vnl_dedupe_lookup', table_name='vendor_notification_logs')
    op.drop_index(op.f('ix_vendor_notification_logs_trigger'), table_name='vendor_notification_logs')
    op.drop_index(op.f('ix_vendor_notification_logs_vendor_id'), table_name='vendor_notification_logs')
    op.drop_table('vendor_notification_logs')
    notification_trigger_enum.drop(op.get_bind(), checkfirst=True)
    notification_channel_enum.drop(op.get_bind(), checkfirst=True)
