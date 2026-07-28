# ─────────────────────────────────────────────────────────────
#  app/repositories/user_repository.py  —  User DB operations
# ─────────────────────────────────────────────────────────────
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Read ──────────────────────────────────────────────────
    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        result = await self.db.execute(
            select(User.id).where(User.email == email.lower())
        )
        return result.scalar_one_or_none() is not None

    async def list_active(self) -> list[User]:
        """All active users — used to populate the Assigned Analyst dropdown."""
        result = await self.db.execute(
            select(User).where(User.is_active == True).order_by(User.full_name)
        )
        return list(result.scalars().all())

    # ── Create ────────────────────────────────────────────────
    async def create(
        self,
        email: str,
        full_name: str,
        hashed_password: str,
        is_admin: bool = False,
        role: UserRole = UserRole.ANALYST,
    ) -> User:
        # Keep is_admin in sync with role rather than letting the two drift —
        # role is the source of truth for permission checks (see app.utils.rbac).
        if is_admin:
            role = UserRole.ADMIN
        user = User(
            email=email.lower(),
            full_name=full_name,
            hashed_password=hashed_password,
            is_admin=(role == UserRole.ADMIN),
            role=role,
        )
        self.db.add(user)
        await self.db.flush()   # get the generated id without committing
        await self.db.refresh(user)
        return user

    # ── Update ────────────────────────────────────────────────
    async def update_password(self, user: User, hashed_password: str) -> User:
        user.hashed_password = hashed_password
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def deactivate(self, user: User) -> User:
        user.is_active = False
        await self.db.flush()
        return user
