# ─────────────────────────────────────────────────────────────
#  app/routes/auth.py  —  Authentication endpoints
# ─────────────────────────────────────────────────────────────
from fastapi import APIRouter, Depends, Request, status
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
from app.utils.rate_limit import limiter

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


# ── Dependency: load the full current user ────────────────────
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user


# ── Dependency: admin-only guard ──────────────────────────────
async def require_admin(current_user=Depends(get_current_user)):
    """Reject non-admin users with 403. Used on every config-management
    endpoint so vendors can never modify configuration (requirement 6)."""
    from app.models.user import UserRole
    is_admin = current_user.role == UserRole.ADMIN or current_user.is_admin
    if not is_admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


# ── Endpoints ─────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@limiter.limit("10/minute")
async def register(
    request: Request,
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
@limiter.limit("10/minute")
async def login(
    request: Request,
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
    user = await ctrl.get_me(user_id)
    # Attach the caller's permission list so the UI can show/hide features in
    # lockstep with what the API will actually authorise (Module 4).
    from app.utils.permissions import permissions_for, role_of
    from app.models.user import User as UserModel
    db_user = await db.get(UserModel, user_id)
    if db_user is not None:
        data = user.model_dump() if hasattr(user, "model_dump") else dict(user)
        data["permissions"] = permissions_for(db_user)
        data["role"] = role_of(db_user).value
        return data
    return user


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
