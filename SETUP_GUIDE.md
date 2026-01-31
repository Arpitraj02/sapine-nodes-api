# 🚀 Sapine Bot Hosting Platform - Quick Setup Guide

## One-Click Installation for Ubuntu

This guide will help you set up the Sapine Bot Hosting Platform API on Ubuntu in just a few minutes with a single command!

## 🎯 What You Get

✅ **Automatic Installation** - Everything installed and configured automatically  
✅ **Secure Setup** - Auto-generated passwords and JWT secrets  
✅ **PostgreSQL Database** - Running in Docker container  
✅ **Python Environment** - Virtual environment with all dependencies  
✅ **Production Ready** - Proper security and error handling  
✅ **Fixed Dependencies** - Pydantic email validation working out of the box  

## 📋 Prerequisites

- **Operating System**: Ubuntu 20.04+ or Debian 11+
- **User Permissions**: sudo access (for installing Docker and system packages)
- **Disk Space**: At least 2GB free space
- **Internet Connection**: Required for downloading packages

## 🚀 Quick Start (One Command!)

```bash
./install.sh
```

That's it! The script will:
1. ✅ Check and install Python 3.8+
2. ✅ Check and install Docker
3. ✅ Generate secure passwords and JWT secrets
4. ✅ Setup PostgreSQL database in Docker
5. ✅ Create Python virtual environment
6. ✅ Install all dependencies (including email-validator for pydantic)
7. ✅ Create bot storage directory
8. ✅ Initialize database
9. ✅ Verify installation

## 🎮 Starting the API

After installation completes, start the API server:

```bash
./start.sh
```

Or manually:

```bash
source venv/bin/activate
python -m app.main
```

The API will be available at:
- 📖 **API Documentation**: http://localhost:8000/docs
- 🔍 **Alternative Docs**: http://localhost:8000/redoc
- ❤️ **Health Check**: http://localhost:8000/health

## 🔧 Manual Installation (Step by Step)

If you prefer to install manually or need more control:

### 1. Install Python

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv
```

### 2. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### 3. Setup PostgreSQL

```bash
docker run -d \
  --name sapine-postgres-db \
  -e POSTGRES_USER=sapine_user \
  -e POSTGRES_PASSWORD=your_secure_password \
  -e POSTGRES_DB=sapine_bots \
  -p 5432:5432 \
  -v sapine-postgres-data:/var/lib/postgresql/data \
  --restart unless-stopped \
  postgres:15-alpine
```

### 4. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
nano .env
```

Update at minimum:
- `DATABASE_URL` with your PostgreSQL credentials
- `JWT_SECRET_KEY` with a secure random key (use `openssl rand -hex 32`)

### 6. Create Bot Storage

```bash
mkdir -p ./bot_storage
chmod 755 ./bot_storage
```

### 7. Start the API

```bash
python -m app.main
```

## 🐛 Fixed Issues

### ✅ Pydantic Email Validator Issue - SOLVED

The "pydantic email library missing" issue has been fixed by adding `email-validator` to the requirements. The API now properly validates email addresses using Pydantic's `EmailStr` type.

**Before:**
```
ModuleNotFoundError: No module named 'email_validator'
```

**After:**
```python
# requirements.txt now includes:
email-validator==2.1.0
```

This enables proper email validation in registration and login endpoints.

## 📝 Environment Variables

The `.env` file contains all configuration:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sapine_bots

# JWT Authentication (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your_generated_secret_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Bot Storage
BOT_STORAGE_PATH=./bot_storage

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Server
HOST=0.0.0.0
PORT=8000
```

## 🎯 Testing the API

### Quick Test Script

Run the automated test script to verify everything works:

```bash
./test-api.sh
```

This will test:
- ✅ Root endpoint
- ✅ Health check
- ✅ User registration
- ✅ User login
- ✅ User profile retrieval
- ✅ Invalid credentials handling
- ✅ Duplicate registration prevention

### Manual Testing

### 1. Check Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "service": "sapine-bot-hosting"}
```

### 2. Register a User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "secure_password_123"
  }'
```

### 3. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "secure_password_123"
  }'
```

### 4. Test Authenticated Endpoint

```bash
# Use the token from login response
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 🔧 Useful Commands

### Database Management

```bash
# Access PostgreSQL
docker exec -it sapine-postgres-db psql -U sapine_user -d sapine_bots

# View database logs
docker logs sapine-postgres-db

# Stop database
docker stop sapine-postgres-db

# Start database
docker start sapine-postgres-db

# Remove database (WARNING: Deletes all data!)
docker rm -f sapine-postgres-db
docker volume rm sapine-postgres-data
```

### Application Management

```bash
# Activate virtual environment
source venv/bin/activate

# Install new dependencies
pip install -r requirements.txt

# Run with auto-reload (development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run in production mode
python -m app.main
```

### Docker Compose (Alternative)

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild and restart
docker-compose up -d --build
```

## 🛡️ Security Features

- ✅ **Password Hashing**: Argon2 (memory-hard, PHC winner)
- ✅ **JWT Authentication**: Secure token-based auth
- ✅ **Email Validation**: Pydantic EmailStr with email-validator
- ✅ **Rate Limiting**: Prevents brute force attacks
- ✅ **Docker Isolation**: Bots run in secure containers
- ✅ **SQL Injection Prevention**: SQLAlchemy ORM
- ✅ **Command Injection Prevention**: Strict validation
- ✅ **Audit Logging**: Track all sensitive actions

## 🎨 API Features

- 👥 Multi-user support with authentication
- 🔐 Role-based access control (USER, ADMIN, OWNER)
- 🐳 Docker container management for bots
- 🐍 Python and Node.js runtime support
- 📦 File and ZIP upload support
- 📊 Real-time log streaming (WebSockets)
- 📝 Comprehensive audit logs
- ⚡ Rate limiting protection

## 🐞 Troubleshooting

### Issue: Docker permission denied

**Solution:**
```bash
sudo usermod -aG docker $USER
# Log out and log back in
```

### Issue: Port 8000 already in use

**Solution:**
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill the process or change PORT in .env file
```

### Issue: Database connection failed

**Solution:**
```bash
# Check if PostgreSQL container is running
docker ps | grep sapine-postgres-db

# Start if stopped
docker start sapine-postgres-db

# Check logs
docker logs sapine-postgres-db
```

### Issue: Email validator not found

**Solution:**
This is now fixed! But if you encounter it:
```bash
source venv/bin/activate
pip install email-validator==2.1.0
```

### Issue: Virtual environment activation fails

**Solution:**
```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📚 Additional Documentation

- 📖 [Full README](README.md) - Complete project documentation
- 🔒 [Security Guide](SECURITY.md) - Security features and best practices
- 🧪 [Testing Guide](Testing.md) - API testing and workflows
- 🏗️ [Architecture](ARCHITECTURE.md) - System architecture details
- 🚀 [Deployment](deployment.md) - Production deployment guide

## 💡 Pro Tips

1. **Use the automatic script** - `./install.sh` handles everything
2. **Start quickly** - Use `./start.sh` after installation
3. **Check the docs** - Visit `/docs` endpoint for interactive API documentation
4. **Secure your secrets** - Never commit `.env` file to git
5. **Use strong passwords** - Let the script generate them automatically
6. **Monitor logs** - Check application and database logs regularly
7. **Regular updates** - Keep dependencies updated with `pip install -U -r requirements.txt`

## 🤝 Need Help?

If you encounter any issues:

1. Check the troubleshooting section above
2. Review the logs: `docker logs sapine-postgres-db`
3. Check API logs in the console
4. Open an issue on GitHub with detailed error messages

## 🎉 Success!

Your Sapine Bot Hosting Platform is now ready to use! Visit http://localhost:8000/docs to explore the API.

Happy hosting! 🚀
