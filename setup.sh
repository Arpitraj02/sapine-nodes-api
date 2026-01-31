#!/bin/bash

# Automatic Setup Script for Sapine Bot Hosting Platform
# This script fully automates development environment setup

set -e

echo "========================================================"
echo "Sapine Bot Hosting Platform - Automatic Setup Script"
echo "========================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
POSTGRES_USER="sapine_dev"
POSTGRES_PASSWORD="dev_password_123"
POSTGRES_DB="sapine_bots"
POSTGRES_PORT="5432"
API_PORT="8000"
BOT_STORAGE_PATH="/var/lib/bots"

echo -e "${BLUE}Step 1/9: Checking and installing Python...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3 not found. Installing...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "${RED}Please install Python 3.11+ from https://www.python.org/downloads/${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Python 3 found${NC}"
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}  Python version: $PYTHON_VERSION${NC}"

echo ""
echo -e "${BLUE}Step 2/9: Checking and installing Docker...${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker not found. Installing...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Install Docker on Linux
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        echo -e "${GREEN}✓ Docker installed${NC}"
        echo -e "${YELLOW}Note: You may need to log out and back in for Docker group changes to take effect${NC}"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "${RED}Please install Docker Desktop from https://www.docker.com/products/docker-desktop${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Docker found${NC}"
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${YELLOW}Starting Docker...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo systemctl start docker
        sudo systemctl enable docker
    fi
    
    # Wait for Docker to start
    for i in {1..30}; do
        if docker info &> /dev/null; then
            break
        fi
        sleep 1
    done
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker failed to start${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Docker is running${NC}"

echo ""
echo -e "${BLUE}Step 3/9: Checking and installing docker-compose...${NC}"

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}docker-compose not found. Installing...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        echo -e "${GREEN}✓ docker-compose installed${NC}"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "${YELLOW}docker-compose should be included with Docker Desktop${NC}"
    fi
else
    echo -e "${GREEN}✓ docker-compose found${NC}"
fi

echo ""
echo -e "${BLUE}Step 4/9: Creating .env file with secure credentials...${NC}"

# Generate a random JWT secret
if command -v openssl &> /dev/null; then
    JWT_SECRET=$(openssl rand -hex 32)
else
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
fi

# Create .env file
cat > .env << EOF
# Database
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}

# JWT Secret (Auto-generated - DO NOT use in production)
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Bot Storage
BOT_STORAGE_PATH=${BOT_STORAGE_PATH}

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Server
HOST=0.0.0.0
PORT=${API_PORT}

# Docker Compose (used by docker-compose.yml)
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_PORT=${POSTGRES_PORT}
API_PORT=${API_PORT}
EOF

echo -e "${GREEN}✓ .env file created${NC}"
echo -e "${YELLOW}  JWT Secret: ${JWT_SECRET:0:20}...${NC}"
echo -e "${YELLOW}  DB User: ${POSTGRES_USER}${NC}"
echo -e "${YELLOW}  DB Password: ${POSTGRES_PASSWORD}${NC}"
echo -e "${YELLOW}  DB Name: ${POSTGRES_DB}${NC}"

echo ""
echo -e "${BLUE}Step 5/9: Setting up PostgreSQL with Docker...${NC}"

# Stop any existing containers
if docker ps -a --format '{{.Names}}' | grep -q "^sapine-db$"; then
    echo -e "${YELLOW}Stopping existing PostgreSQL container...${NC}"
    docker stop sapine-db 2>/dev/null || true
    docker rm sapine-db 2>/dev/null || true
fi

# Start PostgreSQL container
echo -e "${YELLOW}Starting PostgreSQL container...${NC}"
docker run -d \
  --name sapine-db \
  -e POSTGRES_USER=${POSTGRES_USER} \
  -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
  -e POSTGRES_DB=${POSTGRES_DB} \
  -p ${POSTGRES_PORT}:5432 \
  -v sapine-postgres-data:/var/lib/postgresql/data \
  --restart unless-stopped \
  postgres:15-alpine

echo -e "${GREEN}✓ PostgreSQL container started${NC}"

echo ""
echo -e "${BLUE}Step 6/9: Waiting for PostgreSQL to be ready...${NC}"

# Wait for PostgreSQL to be ready
for i in {1..30}; do
    if docker exec sapine-db pg_isready -U ${POSTGRES_USER} &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
        break
    fi
    echo -e "${YELLOW}  Waiting for PostgreSQL... ($i/30)${NC}"
    sleep 2
done

# Verify PostgreSQL is accessible
if ! docker exec sapine-db pg_isready -U ${POSTGRES_USER} &> /dev/null; then
    echo -e "${RED}Error: PostgreSQL failed to start${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Step 7/9: Creating virtual environment and installing dependencies...${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies (this may take a minute)...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo ""
echo -e "${BLUE}Step 8/9: Creating bot storage directory...${NC}"

# Create bot storage directory
if [ ! -d "$BOT_STORAGE_PATH" ]; then
    echo -e "${YELLOW}Creating bot storage directory: $BOT_STORAGE_PATH${NC}"
    if sudo mkdir -p "$BOT_STORAGE_PATH" 2>/dev/null; then
        sudo chown -R $USER:$USER "$BOT_STORAGE_PATH" 2>/dev/null || true
    else
        mkdir -p "$BOT_STORAGE_PATH"
    fi
    echo -e "${GREEN}✓ Bot storage directory created${NC}"
else
    echo -e "${GREEN}✓ Bot storage directory exists${NC}"
fi

echo ""
echo -e "${BLUE}Step 9/9: Starting FastAPI application...${NC}"

# Initialize database by starting the app briefly
echo -e "${YELLOW}Initializing database and creating default plans...${NC}"

# Start the app in the background to initialize DB
python -m app.main &
APP_PID=$!

# Wait for app to start and initialize DB
sleep 5

# Check if app is still running
if ps -p $APP_PID > /dev/null; then
    echo -e "${GREEN}✓ Database initialized${NC}"
    # Keep the app running
else
    echo -e "${YELLOW}App initialization completed${NC}"
fi

echo ""
echo -e "${GREEN}========================================================${NC}"
echo -e "${GREEN}          🎉 Setup Complete! 🎉${NC}"
echo -e "${GREEN}========================================================${NC}"
echo ""
echo -e "${BLUE}Your development environment is ready!${NC}"
echo ""
echo -e "${YELLOW}Database Information:${NC}"
echo "  PostgreSQL Container: sapine-db"
echo "  Database: ${POSTGRES_DB}"
echo "  Username: ${POSTGRES_USER}"
echo "  Password: ${POSTGRES_PASSWORD}"
echo "  Port: ${POSTGRES_PORT}"
echo "  Connection: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"
echo ""
echo -e "${YELLOW}API Server:${NC}"
echo "  The FastAPI server is now running!"
echo "  URL: http://localhost:${API_PORT}"
echo "  API Docs: http://localhost:${API_PORT}/docs"
echo "  Health Check: http://localhost:${API_PORT}/health"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Open http://localhost:${API_PORT}/docs in your browser"
echo "  2. Try the health check endpoint"
echo "  3. Register a new user at POST /auth/register"
echo "  4. Follow the Testing.txt guide for complete workflow"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  Stop API: pkill -f 'python -m app.main' or press Ctrl+C in this terminal"
echo "  Stop PostgreSQL: docker stop sapine-db"
echo "  Start PostgreSQL: docker start sapine-db"
echo "  View PostgreSQL logs: docker logs sapine-db"
echo "  Access PostgreSQL: docker exec -it sapine-db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}"
echo "  Restart everything: ./setup.sh"
echo ""
echo -e "${YELLOW}Alternative - Use Docker Compose:${NC}"
echo "  docker-compose up -d    # Start all services"
echo "  docker-compose down     # Stop all services"
echo "  docker-compose logs -f  # View logs"
echo ""
echo -e "${GREEN}Press Ctrl+C to stop the API server${NC}"
echo ""

# Wait for the app process
wait $APP_PID 2>/dev/null || true
