# Sapine Bot Hosting Platform API

A production-ready backend for a multi-user bot hosting platform with secure Docker execution.

## Features

- **Multi-User Support**: Users can register, login, and manage their own bots
- **Role-Based Access Control**: USER, ADMIN, and OWNER roles with proper permissions
- **Secure Docker Execution**: Bots run in isolated containers with strict security constraints
- **Multiple Runtimes**: Support for Python and Node.js bots
- **File Upload**: Support for zip archives and single file uploads
- **Real-Time Logs**: WebSocket-based log streaming for live console output
- **Resource Limits**: CPU and RAM limits per plan
- **Audit Logging**: Track all security-sensitive actions

## Architecture

```
┌─────────────┐
│   FastAPI   │  ← HTTP/WebSocket API
└──────┬──────┘
       │
┌──────┴──────┐
│   SQLAlchemy │  ← Database ORM
│   PostgreSQL │
└──────┬──────┘
       │
┌──────┴──────┐
│   Docker    │  ← Container Runtime
│   Engine    │
└─────────────┘
```

## Security Features

### Docker Container Security
- No privileged containers
- All Linux capabilities dropped
- CPU and RAM limits enforced
- Network isolation (bridge mode)
- Read-only root filesystem where possible
- No privilege escalation allowed

### Command Validation
- Start commands are validated to prevent shell injection
- No dangerous operators allowed (&&, ||, ;, |, etc.)
- No bash/sh execution
- Command length limited

### File Upload Security
- Filenames sanitized to prevent path traversal
- File extensions validated per runtime
- Files never executed on host
- Extraction performed safely within container

### Authentication & Authorization
- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control (RBAC)
- User status checks (ACTIVE/SUSPENDED)
- Audit logging for sensitive actions

### Rate Limiting
- API endpoints rate-limited per IP
- Prevents abuse and DoS attacks

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Container Runtime**: Docker (docker-py)
- **Authentication**: JWT (python-jose)
- **Password Hashing**: bcrypt (passlib)
- **WebSockets**: FastAPI native
- **Server**: Uvicorn

## Installation

### Quick Start (Automatic Setup)

For rapid setup and development, use our automatic setup script:

```bash
git clone https://github.com/Arpitraj02/sapine-nodes-api.git
cd sapine-nodes-api
./setup.sh
```

This script will automatically:
- Install Python, pip, and virtualenv
- Install Docker and docker-compose
- Create a PostgreSQL container
- Generate secure credentials and .env file
- Install Python dependencies
- Initialize the database
- Start the FastAPI application

**Documentation:**
- [Testing.txt](Testing.txt) - Complete cURL-based testing guide for all endpoints
- [deployment.md](deployment.md) - Step-by-step VPS deployment guide

### Manual Setup

#### Prerequisites
- Python 3.11 or higher
- PostgreSQL 12 or higher
- Docker Engine
- Git

#### Setup Steps

1. Clone the repository:
```bash
git clone https://github.com/Arpitraj02/sapine-nodes-api.git
cd sapine-nodes-api
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET_KEY`: Secret key for JWT tokens (generate with `openssl rand -hex 32`)
- `BOT_STORAGE_PATH`: Path for bot file storage (default: `/var/lib/bots`)

5. Create bot storage directory:
```bash
sudo mkdir -p /var/lib/bots
sudo chown -R $USER:$USER /var/lib/bots
```

6. Initialize the database:
```bash
# Database tables will be created automatically on first run
```

7. Run the application:
```bash
python -m app.main
# Or with uvicorn directly:
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- Interactive API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## Testing

### Complete Testing Guide

For comprehensive cURL-based testing of all endpoints, see [Testing.txt](Testing.txt).

The guide includes:
- User registration and authentication
- Bot creation and management
- Code upload (single files and zip archives)
- Bot lifecycle operations (start/stop/restart)
- WebSocket log streaming
- Admin endpoints
- Complete workflow test script
- Error handling examples
- Troubleshooting tips

### Quick Test

```bash
# Health check
curl http://localhost:8000/health

# Register user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123"}'
```

For detailed testing instructions with example requests and responses, refer to [Testing.txt](Testing.txt).

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info

### Bot Management
- `POST /bots` - Create a new bot
- `GET /bots` - List user's bots
- `POST /bots/{bot_id}/upload` - Upload bot code
- `POST /bots/{bot_id}/start` - Start a bot
- `POST /bots/{bot_id}/stop` - Stop a bot
- `POST /bots/{bot_id}/restart` - Restart a bot
- `DELETE /bots/{bot_id}` - Delete a bot

### WebSocket
- `WS /bots/{bot_id}/logs?token=JWT` - Stream bot logs in real-time

### Admin (ADMIN/OWNER only)
- `GET /admin/users` - List all users
- `POST /admin/users/{user_id}/suspend` - Suspend a user
- `POST /admin/users/{user_id}/activate` - Activate a user

## Usage Example

### 1. Register a User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword123"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Create a Bot
```bash
curl -X POST http://localhost:8000/bots \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-discord-bot",
    "runtime": "python",
    "start_cmd": "python bot.py"
  }'
```

### 3. Upload Bot Code
```bash
curl -X POST http://localhost:8000/bots/1/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@bot.zip"
```

### 4. Start the Bot
```bash
curl -X POST http://localhost:8000/bots/1/start \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Stream Logs (WebSocket)
```javascript
const ws = new WebSocket('ws://localhost:8000/bots/1/logs?token=YOUR_TOKEN');
ws.onmessage = (event) => {
  console.log('Log:', event.data);
};
```

## Supported Runtimes

### Python
- **Image**: `python:3.11-slim`
- **Build Command**: `pip install -r requirements.txt`
- **Default Start**: `python main.py`
- **Allowed Files**: `.py`, `.txt`, `.json`, `.yaml`, `.yml`

### Node.js
- **Image**: `node:20-alpine`
- **Build Command**: `npm install`
- **Default Start**: `node index.js`
- **Allowed Files**: `.js`, `.json`, `.ts`

## Database Models

### User
- Stores user accounts with authentication credentials
- Supports role-based access control (USER/ADMIN/OWNER)
- Tracks account status (ACTIVE/SUSPENDED)

### Plan
- Defines resource limits and bot quotas
- Controls CPU, RAM, and max bot count per user

### Bot
- Represents a hosted bot instance
- Tracks container lifecycle and configuration
- `container_id` is internal only (never exposed via API)

### AuditLog
- Logs security-sensitive actions
- Tracks user actions, IP addresses, and timestamps
- Used for compliance and security monitoring

## Default Plans

Three plans are created on first startup:

1. **Free Plan**
   - Max bots: 1
   - CPU: 0.5 cores
   - RAM: 256MB

2. **Basic Plan**
   - Max bots: 3
   - CPU: 1.0 core
   - RAM: 512MB

3. **Pro Plan**
   - Max bots: 10
   - CPU: 2.0 cores
   - RAM: 1GB

## Deployment

### Production Deployment on Ubuntu VPS

For complete step-by-step production deployment instructions, see [deployment.md](deployment.md).

The guide covers:
- Ubuntu VPS setup and security configuration
- Docker and PostgreSQL installation
- SSL/TLS with Let's Encrypt
- Nginx reverse proxy setup
- Systemd service configuration
- Firewall setup with UFW
- Monitoring and maintenance
- Backup strategies

Quick deployment with Docker Compose:

```bash
# On your VPS
git clone https://github.com/Arpitraj02/sapine-nodes-api.git
cd sapine-nodes-api

# Configure environment
cp .env.example .env
vim .env  # Set production values

# Start services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Docker Deployment (Development)

The included `docker-compose.yml` provides a complete development environment:

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database on port 5432
- FastAPI application on port 8000

Manual Docker setup:

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI (needed to control host Docker)
RUN apt-get update && \
    apt-get install -y docker.io && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create a `docker-compose.yml`:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: sapine_bots
      POSTGRES_USER: sapine
      POSTGRES_PASSWORD: changeme
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - bot_storage:/var/lib/bots
    environment:
      DATABASE_URL: postgresql://sapine:changeme@postgres:5432/sapine_bots
      JWT_SECRET_KEY: your-secret-key-here
      BOT_STORAGE_PATH: /var/lib/bots
    depends_on:
      - postgres

volumes:
  postgres_data:
  bot_storage:
```

Deploy:
```bash
docker-compose up -d
```

### Production Considerations

1. **Environment Variables**
   - Use strong, randomly generated `JWT_SECRET_KEY`
   - Secure database credentials
   - Configure proper `CORS` origins

2. **Database**
   - Use connection pooling
   - Regular backups
   - Monitor performance

3. **Docker**
   - Ensure Docker daemon is running
   - Monitor container resource usage
   - Set up log rotation

4. **Security**
   - Use HTTPS in production
   - Implement rate limiting at reverse proxy level
   - Regular security updates
   - Monitor audit logs

5. **Monitoring**
   - Set up application monitoring (e.g., Prometheus)
   - Configure alerting for container failures
   - Track resource usage per bot

## File Structure

```
sapine-nodes-api/
├── app/
│   ├── __init__.py       # Package initialization
│   ├── main.py           # FastAPI app + routes
│   ├── auth.py           # JWT auth + RBAC
│   ├── db.py             # Database engine & session
│   ├── models.py         # SQLAlchemy models
│   ├── docker.py         # Safe Docker abstraction
│   ├── bots.py           # Bot endpoints + logic
│   ├── sockets.py        # WebSocket log streaming
│   └── utils.py          # Errors, helpers, validators
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Security Considerations

### Command Injection Prevention
The platform validates all user-provided start commands to prevent shell injection attacks. Commands containing dangerous patterns like `&&`, `;`, `|`, or shell invocations are rejected.

### Path Traversal Prevention
All uploaded filenames are sanitized to remove path components and dangerous characters. Files are stored in isolated directories per bot.

### Container Escape Prevention
Containers run with:
- No privileged mode
- All capabilities dropped
- Resource limits enforced
- No access to host filesystem (except mounted code)
- Network isolation

### Container ID Protection
Container IDs are treated as internal implementation details and are never exposed through the API. This prevents users from directly manipulating containers.

### Audit Trail
All security-sensitive actions are logged with user ID, action type, target resource, IP address, and timestamp.

## License

This project is proprietary software. All rights reserved.

## Documentation

- **[README.md](README.md)** - Project overview and setup instructions
- **[Testing.txt](Testing.txt)** - Complete cURL-based testing guide for all endpoints
- **[deployment.md](deployment.md)** - Production deployment guide for Ubuntu VPS
- **[API_TESTING.md](API_TESTING.md)** - Detailed API testing examples
- **[SECURITY.md](SECURITY.md)** - Security guidelines and best practices
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Project overview and features

## Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/Arpitraj02/sapine-nodes-api/issues)
- Check the documentation files listed above
- Review the interactive API docs at `/docs`
