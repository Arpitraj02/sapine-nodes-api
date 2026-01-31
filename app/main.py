"""
Main FastAPI application for the bot hosting platform.
Configures routes, middleware, and application lifecycle.
"""

from fastapi import FastAPI, Request, Depends, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
from datetime import timedelta
from typing import List
import logging
import os

from app.db import get_db, init_db
from app.models import User, UserRole, UserStatus, Plan, AuditLog
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_admin_user
)
from app.utils import validate_email, get_client_ip, rate_limit, BadRequestException, ConflictException
from app.bots import router as bots_router, create_audit_log
from app.sockets import router as ws_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Sapine Bot Hosting API",
    description="Multi-user bot hosting platform with Docker container management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models for Auth
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    status: UserStatus
    created_at: str
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Initialize database and create default data on startup.
    """
    logger.info("Starting Sapine Bot Hosting API...")
    
    # Initialize database tables
    init_db()
    logger.info("Database initialized")
    
    # Create default plans if they don't exist
    from app.db import get_db_context
    with get_db_context() as db:
        # Check if plans exist
        plan_count = db.query(Plan).count()
        if plan_count == 0:
            # Create default plans
            default_plans = [
                Plan(
                    name="Free",
                    max_bots=1,
                    cpu_limit="0.5",
                    ram_limit="256m"
                ),
                Plan(
                    name="Basic",
                    max_bots=3,
                    cpu_limit="1.0",
                    ram_limit="512m"
                ),
                Plan(
                    name="Pro",
                    max_bots=10,
                    cpu_limit="2.0",
                    ram_limit="1g"
                ),
            ]
            for plan in default_plans:
                db.add(plan)
            db.commit()
            logger.info("Default plans created")
    
    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on shutdown.
    """
    logger.info("Shutting down Sapine Bot Hosting API...")


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    """
    return {"status": "healthy", "service": "sapine-bot-hosting"}


# Auth endpoints
@app.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(requests_per_minute=5)
async def register(
    user_data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Creates user with USER role and ACTIVE status by default.
    Returns JWT access token.
    """
    # Validate email format
    if not validate_email(user_data.email):
        raise BadRequestException("Invalid email format")
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise ConflictException("Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=UserRole.USER,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create audit log
    create_audit_log(
        db, user.id, "user_register", str(user.id),
        get_client_ip(request)
    )
    
    logger.info(f"New user registered: {user.email} (ID: {user.id})")
    
    # Generate access token
    access_token = create_access_token(data={"sub": user.id})
    
    return TokenResponse(access_token=access_token)


@app.post("/auth/login", response_model=TokenResponse)
@rate_limit(requests_per_minute=10)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    
    Returns JWT access token on successful authentication.
    """
    # Find user
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is suspended
    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact administrator."
        )
    
    # Create audit log
    create_audit_log(
        db, user.id, "user_login", str(user.id),
        get_client_ip(request)
    )
    
    logger.info(f"User logged in: {user.email} (ID: {user.id})")
    
    # Generate access token
    access_token = create_access_token(data={"sub": user.id})
    
    return TokenResponse(access_token=access_token)


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at.isoformat()
    )


# Admin endpoints
@app.get("/admin/users", response_model=UserListResponse)
async def list_users(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    List all users (ADMIN and OWNER only).
    """
    users = db.query(User).all()
    
    return UserListResponse(
        users=[
            UserResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                status=user.status,
                created_at=user.created_at.isoformat()
            )
            for user in users
        ],
        total=len(users)
    )


@app.post("/admin/users/{user_id}/suspend", status_code=status.HTTP_200_OK)
@rate_limit(requests_per_minute=10)
async def suspend_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Suspend a user account (ADMIN and OWNER only).
    
    Suspended users cannot login or use the platform.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent suspending other admins/owners unless you're an owner
    if user.role in [UserRole.ADMIN, UserRole.OWNER] and current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only OWNER can suspend ADMIN or OWNER accounts"
        )
    
    user.status = UserStatus.SUSPENDED
    db.commit()
    
    # Create audit log
    create_audit_log(
        db, current_user.id, "user_suspend", str(user_id),
        get_client_ip(request),
        f"Suspended by {current_user.email}"
    )
    
    logger.info(f"User {user_id} suspended by {current_user.email}")
    
    return {"message": f"User {user.email} has been suspended"}


@app.post("/admin/users/{user_id}/activate", status_code=status.HTTP_200_OK)
@rate_limit(requests_per_minute=10)
async def activate_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Activate a suspended user account (ADMIN and OWNER only).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = UserStatus.ACTIVE
    db.commit()
    
    # Create audit log
    create_audit_log(
        db, current_user.id, "user_activate", str(user_id),
        get_client_ip(request),
        f"Activated by {current_user.email}"
    )
    
    logger.info(f"User {user_id} activated by {current_user.email}")
    
    return {"message": f"User {user.email} has been activated"}


# Register routers
app.include_router(bots_router)
app.include_router(ws_router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
