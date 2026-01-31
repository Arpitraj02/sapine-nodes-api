"""
WebSocket log streaming for real-time bot console output.
Provides read-only access to container logs.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from jose import JWTError
import logging
import asyncio

from app.db import get_db
from app.models import Bot, User
from app.auth import decode_token
from app.docker import stream_logs, get_recent_logs
from app.bots import verify_bot_ownership

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websockets"])


async def get_current_user_ws(token: str, db: Session) -> User:
    """
    Authenticate WebSocket connection using JWT token.
    """
    try:
        payload = decode_token(token)
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid user ID format in WebSocket token: {user_id_str}")
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        return user
    except JWTError:
        return None


@router.websocket("/bots/{bot_id}/logs")
async def bot_logs_websocket(
    websocket: WebSocket,
    bot_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for streaming bot logs in real-time.
    
    Security:
    - Requires valid JWT token
    - Verifies bot ownership
    - Read-only access (no execution)
    - One connection per bot
    
    Usage:
    ws://host/bots/{bot_id}/logs?token=YOUR_JWT_TOKEN
    """
    await websocket.accept()
    
    try:
        # Authenticate user
        user = await get_current_user_ws(token, db)
        if not user:
            await websocket.send_text("Authentication failed")
            await websocket.close(code=1008)  # Policy violation
            return
        
        # Verify bot ownership
        try:
            bot = verify_bot_ownership(bot_id, user.id, db)
        except Exception as e:
            await websocket.send_text(f"Authorization failed: {str(e)}")
            await websocket.close(code=1008)
            return
        
        if not bot.container_id:
            await websocket.send_text("Bot has no container. Please start the bot first.")
            await websocket.close(code=1000)
            return
        
        logger.info(f"User {user.id} connected to logs for bot {bot_id}")
        
        # Send recent logs first
        recent_logs = get_recent_logs(bot.container_id, tail=50)
        if recent_logs:
            await websocket.send_text(f"=== Recent Logs ===\n{recent_logs}\n=== Live Stream ===\n")
        
        # Stream logs in real-time
        async def stream_to_websocket():
            try:
                for log_line in stream_logs(bot.container_id):
                    await websocket.send_text(log_line)
                    await asyncio.sleep(0.01)  # Small delay to prevent overwhelming
            except Exception as e:
                logger.error(f"Error streaming logs: {e}")
                await websocket.send_text(f"Error: {str(e)}")
        
        # Start streaming
        await stream_to_websocket()
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for bot {bot_id}")
    except Exception as e:
        logger.error(f"WebSocket error for bot {bot_id}: {e}")
        try:
            await websocket.send_text(f"Error: {str(e)}")
            await websocket.close(code=1011)  # Internal error
        except:
            pass
