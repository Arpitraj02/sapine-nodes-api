"""
Database models for the bot hosting platform.
Defines User, Plan, Bot, and AuditLog tables with proper relationships.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db import Base


class UserRole(str, enum.Enum):
    """User role enumeration for RBAC"""
    USER = "USER"
    ADMIN = "ADMIN"
    OWNER = "OWNER"


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class BotStatus(str, enum.Enum):
    """Bot container status"""
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    CRASHED = "CRASHED"


class BotRuntime(str, enum.Enum):
    """Supported bot runtimes"""
    PYTHON = "python"
    NODE = "node"


class SourceType(str, enum.Enum):
    """Type of source upload"""
    ZIP = "zip"
    FILE = "file"


class User(Base):
    """
    User model for authentication and authorization.
    Supports role-based access control and account status management.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    bots = relationship("Bot", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")


class Plan(Base):
    """
    Subscription plan model defining resource limits per user.
    Controls max bots, CPU, and RAM allocation.
    """
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    max_bots = Column(Integer, nullable=False, default=1)
    cpu_limit = Column(String(50), nullable=False, default="0.5")  # e.g., "0.5" for 50% of one CPU
    ram_limit = Column(String(50), nullable=False, default="256m")  # e.g., "256m" for 256MB

    # Relationships
    bots = relationship("Bot", back_populates="plan")


class Bot(Base):
    """
    Bot model representing a user's hosted bot instance.
    Tracks Docker container lifecycle and configuration.
    
    Security: container_id is INTERNAL ONLY and never exposed via API.
    """
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    runtime = Column(SQLEnum(BotRuntime), nullable=False)
    name = Column(String(100), nullable=False)
    
    # INTERNAL ONLY - Never expose through API
    container_id = Column(String(255), nullable=True, index=True)
    
    status = Column(SQLEnum(BotStatus), default=BotStatus.CREATED, nullable=False)
    start_cmd = Column(String(500), nullable=True)  # User-provided start command (validated)
    source_type = Column(SQLEnum(SourceType), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="bots")
    plan = relationship("Plan", back_populates="bots")


class AuditLog(Base):
    """
    Audit log for tracking sensitive actions and security events.
    Used for compliance and security monitoring.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g., "bot_start", "user_suspend"
    target_id = Column(String(100), nullable=True)  # ID of affected resource (bot_id, user_id, etc.)
    ip_address = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)  # Additional context as JSON string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
