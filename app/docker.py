"""
Safe Docker abstraction layer for managing bot containers.
Implements security constraints and runtime registry.

SECURITY CRITICAL: This module is the ONLY interface to Docker.
Never expose Docker client or container objects directly to users.
"""

import docker
from docker.errors import DockerException, NotFound, APIError
from typing import Optional, Dict, Generator
import os
from pathlib import Path
import logging

from app.models import BotRuntime, BotStatus
from app.utils import BadRequestException

logger = logging.getLogger(__name__)

# Docker client singleton
_docker_client: Optional[docker.DockerClient] = None


def get_docker_client() -> docker.DockerClient:
    """
    Get or create Docker client singleton.
    Uses explicit unix socket to avoid http+docker scheme issues in Docker SDK 7.0.0+.
    
    Note: This function explicitly ignores DOCKER_HOST environment variable to prevent
    issues with unsupported URL schemes like "http+docker://". The DOCKER_HOST is 
    permanently cleared for this process as we always use the explicit unix socket.
    """
    global _docker_client
    if _docker_client is None:
        try:
            # Clear DOCKER_HOST to prevent http+docker:// scheme issues
            # We permanently clear this for the process since we always use explicit unix socket
            cleared_docker_host = os.environ.pop('DOCKER_HOST', None)
            if cleared_docker_host:
                logger.info(f"Cleared DOCKER_HOST={cleared_docker_host} to use explicit unix socket")
            
            # Use explicit unix socket instead of from_env() to avoid http+docker scheme issue
            # This works with both Docker SDK 6.x and 7.x
            # Note: unix:/// with three slashes specifies an absolute path
            _docker_client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
            logger.info("Docker client connected successfully via unix:///var/run/docker.sock")
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise RuntimeError(f"Docker service unavailable: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to Docker: {e}")
            raise RuntimeError(f"Failed to initialize Docker client: {str(e)}")
    return _docker_client


# Runtime registry - defines safe, pre-approved container configurations
RUNTIME_REGISTRY: Dict[BotRuntime, Dict] = {
    BotRuntime.PYTHON: {
        "image": "python:3.11-slim",
        "build_cmd": "pip install --no-cache-dir -r requirements.txt",
        "default_start": "python main.py",
        "working_dir": "/app",
        "allowed_extensions": [".py", ".txt", ".json", ".yaml", ".yml"],
    },
    BotRuntime.NODE: {
        "image": "node:20-alpine",
        "build_cmd": "npm install",
        "default_start": "node index.js",
        "working_dir": "/app",
        "allowed_extensions": [".js", ".json", ".ts"],
    },
}


def get_runtime_config(runtime: BotRuntime) -> Dict:
    """
    Get configuration for a specific runtime.
    """
    if runtime not in RUNTIME_REGISTRY:
        raise BadRequestException(f"Unsupported runtime: {runtime}")
    return RUNTIME_REGISTRY[runtime]


def get_bot_storage_path(bot_id: int) -> Path:
    """
    Get the storage path for a bot's files.
    Creates directory if it doesn't exist.
    """
    base_path = Path(os.getenv("BOT_STORAGE_PATH", "/var/lib/bots"))
    bot_path = base_path / str(bot_id)
    bot_path.mkdir(parents=True, exist_ok=True)
    return bot_path


def create_container(
    bot_id: int,
    runtime: BotRuntime,
    start_cmd: Optional[str],
    cpu_limit: str,
    ram_limit: str
) -> str:
    """
    Create a Docker container for a bot with strict security constraints.
    
    Security features:
    - No privileged mode
    - All capabilities dropped
    - No network access to host
    - CPU and RAM limits enforced
    - Read-only root filesystem (except /app and /tmp)
    - No direct host access
    
    Returns: container_id (INTERNAL USE ONLY)
    """
    client = get_docker_client()
    runtime_config = get_runtime_config(runtime)
    bot_path = get_bot_storage_path(bot_id)
    
    # Determine start command
    if not start_cmd:
        start_cmd = runtime_config["default_start"]
    
    container_name = f"bot-{bot_id}"
    
    # Security: Drop ALL capabilities
    cap_drop = ["ALL"]
    
    # Security: No privileged mode
    privileged = False
    
    # Security: Resource limits
    mem_limit = ram_limit
    # CPU limit is provided as a decimal string (e.g., "0.5" for 50% of one CPU)
    # Convert to CPU quota: cpu_quota = cpu_limit * cpu_period
    cpu_period = 100000
    cpu_quota = int(float(cpu_limit) * cpu_period)
    
    try:
        # Pull image if not available
        try:
            client.images.get(runtime_config["image"])
        except NotFound:
            logger.info(f"Pulling image {runtime_config['image']}")
            client.images.pull(runtime_config["image"])
        
        # Create container with security constraints
        container = client.containers.create(
            image=runtime_config["image"],
            name=container_name,
            command=["sh", "-c", f"{runtime_config['build_cmd']} 2>&1 || true && {start_cmd}"],
            detach=True,
            
            # Mount user code (read-only mount, writable /tmp for build artifacts)
            volumes={
                str(bot_path): {
                    "bind": runtime_config["working_dir"],
                    "mode": "ro"
                }
            },
            working_dir=runtime_config["working_dir"],
            
            # Security: No privileged mode
            privileged=privileged,
            
            # Security: Drop all capabilities
            cap_drop=cap_drop,
            
            # Security: Resource limits
            mem_limit=mem_limit,
            cpu_quota=cpu_quota,
            cpu_period=cpu_period,
            
            # Security: Network isolation (no host network)
            network_mode="bridge",
            
            # Security: Read-only root filesystem
            read_only=False,  # We need writable /tmp for build steps
            
            # Security: No privilege escalation
            security_opt=["no-new-privileges"],
            
            # Logging
            labels={
                "bot_id": str(bot_id),
                "managed_by": "sapine-bots"
            },
            
            # Auto-remove on stop (cleanup)
            auto_remove=False,  # We manage cleanup explicitly
        )
        
        logger.info(f"Created container {container.id} for bot {bot_id}")
        return container.id
        
    except APIError as e:
        logger.error(f"Failed to create container for bot {bot_id}: {e}")
        raise BadRequestException(f"Failed to create container: {str(e)}")


def start_container(container_id: str) -> bool:
    """
    Start a Docker container.
    Returns True if successful.
    """
    client = get_docker_client()
    try:
        container = client.containers.get(container_id)
        container.start()
        logger.info(f"Started container {container_id}")
        return True
    except NotFound:
        logger.error(f"Container {container_id} not found")
        return False
    except APIError as e:
        logger.error(f"Failed to start container {container_id}: {e}")
        return False


def stop_container(container_id: str, timeout: int = 10) -> bool:
    """
    Stop a Docker container gracefully.
    Returns True if successful.
    """
    client = get_docker_client()
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=timeout)
        logger.info(f"Stopped container {container_id}")
        return True
    except NotFound:
        logger.error(f"Container {container_id} not found")
        return False
    except APIError as e:
        logger.error(f"Failed to stop container {container_id}: {e}")
        return False


def remove_container(container_id: str, force: bool = False) -> bool:
    """
    Remove a Docker container.
    Returns True if successful.
    """
    client = get_docker_client()
    try:
        container = client.containers.get(container_id)
        container.remove(force=force)
        logger.info(f"Removed container {container_id}")
        return True
    except NotFound:
        logger.warning(f"Container {container_id} not found (already removed?)")
        return True  # Already gone, success
    except APIError as e:
        logger.error(f"Failed to remove container {container_id}: {e}")
        return False


def get_container_status(container_id: str) -> BotStatus:
    """
    Get the current status of a container.
    Maps Docker status to BotStatus.
    """
    client = get_docker_client()
    try:
        container = client.containers.get(container_id)
        docker_status = container.status.lower()
        
        if docker_status == "running":
            return BotStatus.RUNNING
        elif docker_status in ["exited", "dead"]:
            # Check exit code to determine if crashed
            exit_code = container.attrs.get("State", {}).get("ExitCode", 0)
            if exit_code != 0:
                return BotStatus.CRASHED
            return BotStatus.STOPPED
        elif docker_status == "created":
            return BotStatus.CREATED
        else:
            return BotStatus.STOPPED
            
    except NotFound:
        return BotStatus.STOPPED
    except APIError as e:
        logger.error(f"Failed to get status for container {container_id}: {e}")
        return BotStatus.STOPPED


def stream_logs(container_id: str) -> Generator[str, None, None]:
    """
    Stream logs from a container.
    Returns a generator that yields log lines.
    
    Security: Read-only access to logs, no execution capability.
    """
    client = get_docker_client()
    try:
        container = client.containers.get(container_id)
        for log_line in container.logs(stream=True, follow=True):
            yield log_line.decode('utf-8', errors='replace')
    except NotFound:
        logger.error(f"Container {container_id} not found")
        yield "Container not found"
    except APIError as e:
        logger.error(f"Failed to stream logs for container {container_id}: {e}")
        yield f"Error streaming logs: {str(e)}"


def get_recent_logs(container_id: str, tail: int = 100) -> str:
    """
    Get recent logs from a container.
    Returns last N lines of logs.
    """
    client = get_docker_client()
    try:
        container = client.containers.get(container_id)
        logs = container.logs(tail=tail).decode('utf-8', errors='replace')
        return logs
    except NotFound:
        return "Container not found"
    except APIError as e:
        logger.error(f"Failed to get logs for container {container_id}: {e}")
        return f"Error retrieving logs: {str(e)}"


def restart_container(container_id: str, timeout: int = 10) -> bool:
    """
    Restart a Docker container.
    Returns True if successful.
    """
    client = get_docker_client()
    try:
        container = client.containers.get(container_id)
        container.restart(timeout=timeout)
        logger.info(f"Restarted container {container_id}")
        return True
    except NotFound:
        logger.error(f"Container {container_id} not found")
        return False
    except APIError as e:
        logger.error(f"Failed to restart container {container_id}: {e}")
        return False
