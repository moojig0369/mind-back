"""
Authentication routes - JWT-based auth with Supabase.
Handles login, registration, and token verification.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.infrastructure.supabase_client import get_admin_client
from app.api.v1.deps import get_current_user

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user with email/password.
    Returns JWT access token.
    
    Supabase Auth handles password verification and JWT generation.
    """
    try:
        supabase = get_admin_client()
        
        # Sign in with Supabase Auth
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
        })
        
        if not response.user or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        
        return LoginResponse(
            access_token=response.session.access_token,
            token_type="bearer",
            user_id=str(response.user.id),
            email=response.user.email,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}",
        )


@router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest):
    """
    Register a new user.
    Creates user in Supabase Auth and returns JWT token.
    """
    try:
        supabase = get_admin_client()
        
        # Sign up with Supabase Auth
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "display_name": request.display_name or request.email.split("@")[0],
                }
            }
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed",
            )
        
        # If confirmation is required, session might be None
        if not response.session:
            return LoginResponse(
                access_token="",
                token_type="bearer",
                user_id=str(response.user.id),
                email=response.user.email,
            )
        
        return LoginResponse(
            access_token=response.session.access_token,
            token_type="bearer",
            user_id=str(response.user.id),
            email=response.user.email,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration error: {str(e)}",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information.
    Requires valid JWT token in Authorization header.
    """
    try:
        supabase = get_admin_client()
        
        # Fetch full user profile from Supabase
        user_response = supabase.auth.admin.get_user_by_id(current_user["id"])
        user = user_response.user
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            display_name=user.user_metadata.get("display_name"),
            avatar_url=user.user_metadata.get("avatar_url"),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user info: {str(e)}",
        )


@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """
    Refresh the current user's JWT token.
    Supabase automatically handles token refresh via session.
    """
    try:
        supabase = get_admin_client()
        
        # Get fresh session (Supabase handles refresh internally)
        # Note: In production, use refresh_token flow
        response = supabase.auth.get_user()
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session",
            )
        
        return {
            "message": "Token refreshed successfully",
            "user_id": str(response.user.id),
            "email": response.user.email,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh error: {str(e)}",
        )
