#!/bin/bash

# Startup script for Sapine Bot Hosting Platform
# This script helps set up and run the application

set -e

echo "================================================"
echo "Sapine Bot Hosting Platform - Setup Script"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 found${NC}"

# Check Python version
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
REQUIRED_VERSION="3.11"
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${YELLOW}Warning: Python $PYTHON_VERSION found, but $REQUIRED_VERSION or higher is recommended${NC}"
fi

# Check if PostgreSQL is accessible
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}Warning: PostgreSQL client not found. Make sure PostgreSQL is running.${NC}"
fi

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker found and running${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip > /dev/null
pip install -r requirements.txt > /dev/null
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    
    # Generate a random JWT secret
    JWT_SECRET=$(openssl rand -hex 32 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}OpenSSL not available, using Python to generate secret...${NC}"
        JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    fi
    
    # Update .env with generated secret
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-secret-key-here-change-in-production/$JWT_SECRET/" .env
    else
        # Linux
        sed -i "s/your-secret-key-here-change-in-production/$JWT_SECRET/" .env
    fi
    
    echo -e "${GREEN}✓ .env file created with random JWT secret${NC}"
    echo -e "${YELLOW}Please review and update .env file with your database credentials${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Create bot storage directory
BOT_STORAGE_PATH=$(grep BOT_STORAGE_PATH .env | cut -d '=' -f2 || echo "/var/lib/bots")
if [ ! -d "$BOT_STORAGE_PATH" ]; then
    echo -e "${YELLOW}Creating bot storage directory: $BOT_STORAGE_PATH${NC}"
    sudo mkdir -p "$BOT_STORAGE_PATH" || mkdir -p "$BOT_STORAGE_PATH"
    sudo chown -R $USER:$USER "$BOT_STORAGE_PATH" 2>/dev/null || chown -R $USER:$USER "$BOT_STORAGE_PATH"
    echo -e "${GREEN}✓ Bot storage directory created${NC}"
else
    echo -e "${GREEN}✓ Bot storage directory exists${NC}"
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "To start the server:"
echo "  1. Ensure PostgreSQL is running"
echo "  2. Update .env with your database credentials"
echo "  3. Run: python -m app.main"
echo ""
echo "Or use Docker Compose:"
echo "  docker-compose up -d"
echo ""
echo "API Documentation will be available at:"
echo "  http://localhost:8000/docs"
echo ""
