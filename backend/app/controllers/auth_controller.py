# ─────────────────────────────────────────────────────────────
#  app/controllers/auth_controller.py  —  Auth business logic
# ─────────────────────────────────────────────────────────────
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    RegisterRequest, RegisterResponse, UserResponse,
    LoginRequest, TokenResponse, RefreshRequest,
    ChangePasswordRequest, TokenData,
)
from app.utils.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, access_token_expire_seconds,
)
from app.utils.exceptions import (
    AuthenticationError, ConflictError, AuthorizationError, ValidationError
)
from app.models.user import User


class AuthController:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    # ── Register ──────────────────────────────────────────────
    async def register(self, data: RegisterRequest) -> RegisterResponse:
        if await self.repo.exists_by_email(data.email):
            raise ConflictError("An account with this email already exists")

        hashed = hash_password(data.password)
        user = await self.repo.create(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hashed,
        )
        logger.info(f"New user registered: {user.email}")
        return RegisterResponse(user=UserResponse.model_validate(user))

    # ── Login ─────────────────────────────────────────────────
    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthorizationError("Account is deactivated. Contact support.")

        access_token = create_access_token(user.id, user.email)
        refresh_token = create_refresh_token(user.id, user.email)
        logger.info(f"User logged in: {user.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=access_token_expire_seconds(),
        )

    # ── Refresh token ─────────────────────────────────────────
    async def refresh(self, data: RefreshRequest) -> TokenResponse:
        token_data: TokenData = decode_token(data.refresh_token)
        if not token_data or token_data.token_type != "refresh":
            raise AuthenticationError("Invalid or expired refresh token")

        user = await self.repo.get_by_id(token_data.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or deactivated")

        access_token = create_access_token(user.id, user.email)
        refresh_token = create_refresh_token(user.id, user.email)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=access_token_expire_seconds(),
        )

    # ── Get current user ──────────────────────────────────────
    async def get_me(self, user_id: str) -> UserResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        return UserResponse.model_validate(user)

    # ── Change password ───────────────────────────────────────
    async def change_password(
        self, user_id: str, data: ChangePasswordRequest
    ) -> dict:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        if not verify_password(data.current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")

        hashed = hash_password(data.new_password)
        await self.repo.update_password(user, hashed)
        logger.info(f"Password changed for user: {user.email}")
        return {"message": "Password changed successfully"}
