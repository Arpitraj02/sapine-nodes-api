"""
Bot management endpoints and business logic.
Handles bot CRUD operations, file uploads, and lifecycle management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
import shutil
import zipfile
from pathlib import Path
import logging

from app.db import get_db
from app.models import User, Bot, BotStatus, BotRuntime, SourceType, Plan, AuditLog
from app.auth import get_current_user
from app.docker import (
    create_container, start_container, stop_container, 
    restart_container, get_container_status, get_bot_storage_path,
    get_runtime_config, remove_container
)
from app.utils import (
    validate_start_command, validate_bot_name, sanitize_filename,
    NotFoundException, ForbiddenException, BadRequestException,
    ConflictException, get_client_ip, rate_limit
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bots", tags=["bots"])


# Request/Response models
class BotCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    runtime: BotRuntime
    start_cmd: Optional[str] = None
    plan_id: int = 1  # Default to basic plan


class BotResponse(BaseModel):
    id: int
    name: str
    runtime: BotRuntime
    status: BotStatus
    start_cmd: Optional[str]
    source_type: Optional[SourceType]
    created_at: str
    
    class Config:
        from_attributes = True


class BotListResponse(BaseModel):
    bots: List[BotResponse]
    total: int


def verify_bot_ownership(bot_id: int, user_id: int, db: Session) -> Bot:
    """
    Verify that a bot belongs to a user and return the bot.
    Raises NotFoundException if bot doesn't exist.
    Raises ForbiddenException if user doesn't own the bot.
    """
    bot = db.query(Bot).filter(Bot.id == bot_id).first()
    if not bot:
        raise NotFoundException("Bot not found")
    
    if bot.user_id != user_id:
        raise ForbiddenException("You don't have access to this bot")
    
    return bot


def create_audit_log(
    db: Session,
    user_id: int,
    action: str,
    target_id: str,
    ip_address: str,
    details: Optional[str] = None
):
    """
    Create an audit log entry for security-sensitive actions.
    """
    audit = AuditLog(
        user_id=user_id,
        action=action,
        target_id=target_id,
        ip_address=ip_address,
        details=details
    )
    db.add(audit)
    db.commit()


@router.post("", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(requests_per_minute=10)
async def create_bot(
    bot_data: BotCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new bot instance.
    
    Security:
    - Validates bot name format
    - Validates start command for shell injection
    - Enforces plan limits
    - Logs creation action
    """
    # Validate bot name
    if not validate_bot_name(bot_data.name):
        raise BadRequestException(
            "Invalid bot name. Use 3-50 alphanumeric characters, hyphens, or underscores."
        )
    
    # Validate start command if provided
    if bot_data.start_cmd and not validate_start_command(bot_data.start_cmd):
        raise BadRequestException(
            "Invalid start command. Command contains dangerous patterns."
        )
    
    # Check plan exists
    plan = db.query(Plan).filter(Plan.id == bot_data.plan_id).first()
    if not plan:
        raise NotFoundException("Plan not found")
    
    # Check user hasn't exceeded bot limit
    user_bot_count = db.query(Bot).filter(Bot.user_id == current_user.id).count()
    if user_bot_count >= plan.max_bots:
        raise ConflictException(
            f"Bot limit reached. Your plan allows maximum {plan.max_bots} bots."
        )
    
    # Check for duplicate bot name (per user)
    existing = db.query(Bot).filter(
        Bot.user_id == current_user.id,
        Bot.name == bot_data.name
    ).first()
    if existing:
        raise ConflictException("A bot with this name already exists")
    
    # Create bot record
    bot = Bot(
        user_id=current_user.id,
        plan_id=bot_data.plan_id,
        runtime=bot_data.runtime,
        name=bot_data.name,
        start_cmd=bot_data.start_cmd,
        status=BotStatus.CREATED
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    
    # Create storage directory
    get_bot_storage_path(bot.id)
    
    # Audit log
    create_audit_log(
        db, current_user.id, "bot_create", str(bot.id),
        get_client_ip(request)
    )
    
    logger.info(f"User {current_user.id} created bot {bot.id}")
    
    return BotResponse(
        id=bot.id,
        name=bot.name,
        runtime=bot.runtime,
        status=bot.status,
        start_cmd=bot.start_cmd,
        source_type=bot.source_type,
        created_at=bot.created_at.isoformat()
    )


@router.get("", response_model=BotListResponse)
async def list_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all bots owned by the current user.
    """
    bots = db.query(Bot).filter(Bot.user_id == current_user.id).all()
    
    return BotListResponse(
        bots=[
            BotResponse(
                id=bot.id,
                name=bot.name,
                runtime=bot.runtime,
                status=bot.status,
                start_cmd=bot.start_cmd,
                source_type=bot.source_type,
                created_at=bot.created_at.isoformat()
            )
            for bot in bots
        ],
        total=len(bots)
    )


@router.post("/{bot_id}/upload", status_code=status.HTTP_200_OK)
@rate_limit(requests_per_minute=5)
async def upload_bot_files(
    bot_id: int,
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload bot source code (zip or single file).
    
    Security:
    - Validates file extensions
    - Sanitizes filenames
    - Extracts files safely
    - Never executes uploaded code on host
    """
    bot = verify_bot_ownership(bot_id, current_user.id, db)
    runtime_config = get_runtime_config(bot.runtime)
    bot_path = get_bot_storage_path(bot_id)
    
    # Clean existing files (except keep .gitkeep if exists)
    for item in bot_path.glob("*"):
        if item.name != ".gitkeep":
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    
    filename = sanitize_filename(file.filename or "upload")
    
    # Handle zip files
    if filename.endswith('.zip'):
        zip_path = bot_path / filename
        
        # Save zip file
        with open(zip_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        # Extract safely
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Security: Check for path traversal in zip
                for member in zip_ref.namelist():
                    # Prevent path traversal
                    member_path = Path(member)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        raise BadRequestException("Invalid file path in zip")
                    
                    # Check file extension
                    if member.endswith('/'):  # Directory
                        continue
                    
                    ext = Path(member).suffix
                    if ext and ext not in runtime_config["allowed_extensions"]:
                        raise BadRequestException(
                            f"File type {ext} not allowed for {bot.runtime} runtime"
                        )
                
                # Extract all files
                zip_ref.extractall(bot_path)
            
            # Remove zip file after extraction
            zip_path.unlink()
            
            bot.source_type = SourceType.ZIP
            
        except zipfile.BadZipFile:
            raise BadRequestException("Invalid zip file")
        
    else:
        # Handle single file upload
        ext = Path(filename).suffix
        if ext not in runtime_config["allowed_extensions"]:
            raise BadRequestException(
                f"File type {ext} not allowed for {bot.runtime} runtime"
            )
        
        file_path = bot_path / filename
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        bot.source_type = SourceType.FILE
    
    db.commit()
    
    # Audit log
    create_audit_log(
        db, current_user.id, "bot_upload", str(bot_id),
        get_client_ip(request), f"Uploaded {filename}"
    )
    
    logger.info(f"User {current_user.id} uploaded files to bot {bot_id}")
    
    return {"message": "Files uploaded successfully", "filename": filename}


@router.post("/{bot_id}/start", response_model=BotResponse)
@rate_limit(requests_per_minute=10)
async def start_bot(
    bot_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a bot's container.
    
    Creates container if it doesn't exist, then starts it.
    Updates bot status in database.
    """
    bot = verify_bot_ownership(bot_id, current_user.id, db)
    
    # Get plan for resource limits
    plan = db.query(Plan).filter(Plan.id == bot.plan_id).first()
    if not plan:
        raise NotFoundException("Plan not found")
    
    # Check if files have been uploaded
    bot_path = get_bot_storage_path(bot_id)
    if not any(bot_path.iterdir()):
        raise BadRequestException("No files uploaded. Please upload bot code first.")
    
    try:
        # Create container if doesn't exist
        if not bot.container_id:
            container_id = create_container(
                bot_id=bot.id,
                runtime=bot.runtime,
                start_cmd=bot.start_cmd,
                cpu_limit=plan.cpu_limit,
                ram_limit=plan.ram_limit
            )
            bot.container_id = container_id
            db.commit()
        
        # Start container
        success = start_container(bot.container_id)
        if not success:
            raise BadRequestException("Failed to start container")
        
        # Update status
        bot.status = BotStatus.RUNNING
        db.commit()
        
        # Audit log
        create_audit_log(
            db, current_user.id, "bot_start", str(bot_id),
            get_client_ip(request)
        )
        
        logger.info(f"User {current_user.id} started bot {bot_id}")
        
    except Exception as e:
        bot.status = BotStatus.CRASHED
        db.commit()
        raise BadRequestException(f"Failed to start bot: {str(e)}")
    
    return BotResponse(
        id=bot.id,
        name=bot.name,
        runtime=bot.runtime,
        status=bot.status,
        start_cmd=bot.start_cmd,
        source_type=bot.source_type,
        created_at=bot.created_at.isoformat()
    )


@router.post("/{bot_id}/stop", response_model=BotResponse)
@rate_limit(requests_per_minute=10)
async def stop_bot(
    bot_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stop a bot's container.
    """
    bot = verify_bot_ownership(bot_id, current_user.id, db)
    
    if not bot.container_id:
        raise BadRequestException("Bot has no container")
    
    success = stop_container(bot.container_id)
    if not success:
        raise BadRequestException("Failed to stop container")
    
    bot.status = BotStatus.STOPPED
    db.commit()
    
    # Audit log
    create_audit_log(
        db, current_user.id, "bot_stop", str(bot_id),
        get_client_ip(request)
    )
    
    logger.info(f"User {current_user.id} stopped bot {bot_id}")
    
    return BotResponse(
        id=bot.id,
        name=bot.name,
        runtime=bot.runtime,
        status=bot.status,
        start_cmd=bot.start_cmd,
        source_type=bot.source_type,
        created_at=bot.created_at.isoformat()
    )


@router.post("/{bot_id}/restart", response_model=BotResponse)
@rate_limit(requests_per_minute=10)
async def restart_bot(
    bot_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Restart a bot's container.
    """
    bot = verify_bot_ownership(bot_id, current_user.id, db)
    
    if not bot.container_id:
        raise BadRequestException("Bot has no container")
    
    success = restart_container(bot.container_id)
    if not success:
        raise BadRequestException("Failed to restart container")
    
    bot.status = BotStatus.RUNNING
    db.commit()
    
    # Audit log
    create_audit_log(
        db, current_user.id, "bot_restart", str(bot_id),
        get_client_ip(request)
    )
    
    logger.info(f"User {current_user.id} restarted bot {bot_id}")
    
    return BotResponse(
        id=bot.id,
        name=bot.name,
        runtime=bot.runtime,
        status=bot.status,
        start_cmd=bot.start_cmd,
        source_type=bot.source_type,
        created_at=bot.created_at.isoformat()
    )


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit(requests_per_minute=10)
async def delete_bot(
    bot_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a bot and its container.
    """
    bot = verify_bot_ownership(bot_id, current_user.id, db)
    
    # Remove container if exists
    if bot.container_id:
        remove_container(bot.container_id, force=True)
    
    # Remove bot files
    bot_path = get_bot_storage_path(bot_id)
    if bot_path.exists():
        shutil.rmtree(bot_path)
    
    # Delete from database
    db.delete(bot)
    db.commit()
    
    # Audit log
    create_audit_log(
        db, current_user.id, "bot_delete", str(bot_id),
        get_client_ip(request)
    )
    
    logger.info(f"User {current_user.id} deleted bot {bot_id}")
