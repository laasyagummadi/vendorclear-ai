# ─────────────────────────────────────────────────────────────
#  app/routes/auth.py  —  Authentication endpoints
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.controllers.auth_controller import AuthController
from app.schemas.auth import (
    RegisterRequest, RegisterResponse,
    LoginRequest, TokenResponse,
    RefreshRequest, ChangePasswordRequest, UserResponse,
)
from app.schemas.common import SuccessResponse
from app.utils.security import decode_token
from app.utils.exceptions import AuthenticationError

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


# ── Dependency: extract + validate Bearer token ───────────────
async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> str:
    token_data = decode_token(credentials.credentials)
    if not token_data or token_data.token_type != "access":
        raise AuthenticationError("Invalid or expired token")
    return token_data.user_id


# ── Endpoints ─────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    ctrl = AuthController(db)
    return await ctrl.register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access + refresh tokens",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    ctrl = AuthController(db)
    return await ctrl.login(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for new tokens",
)
async def refresh_token(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    ctrl = AuthController(db)
    return await ctrl.refresh(data)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ctrl = AuthController(db)
    return await ctrl.get_me(user_id)


@router.post(
    "/change-password",
    response_model=SuccessResponse,
    summary="Change current user's password",
)
async def change_password(
    data: ChangePasswordRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    ctrl = AuthController(db)
    result = await ctrl.change_password(user_id, data)
    return SuccessResponse(message=result["message"])
