"""add user role (RBAC)

Revision ID: 888ff8141fd1
Revises: e6371a8e2f8c
Create Date: 2026-07-22 06:00:00.000000

Adds `users.role` (ADMIN / ANALYST / VENDOR / AUDITOR) for Feature 7 —
Role-Based Access Control. Backfills existing rows from the legacy
`is_admin` boolean so nobody's access silently changes on upgrade:
  - is_admin = true  -> role = ADMIN
  - is_admin = false -> role = ANALYST (matches prior behavior, where
    every non-admin account could already do everything an analyst can)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '888ff8141fd1'
down_revision: Union[str, None] = 'e6371a8e2f8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role_enum = sa.Enum(
    'ADMIN', 'ANALYST', 'VENDOR', 'AUDITOR', name='userrole'
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)

    op.add_column(
        'users',
        sa.Column('role', user_role_enum, nullable=False, server_default='ANALYST'),
    )
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)

    # Backfill: anyone who was already an admin keeps admin-level access.
    op.execute("UPDATE users SET role = 'ADMIN' WHERE is_admin = true")


def downgrade() -> None:
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_column('users', 'role')
    user_role_enum.drop(op.get_bind(), checkfirst=True)
