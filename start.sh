#!/bin/bash

################################################################################
# Quick Start Script - Sapine Bot Hosting Platform
# 
# This script quickly starts the API server with proper environment
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Sapine Bot Hosting Platform - Quick Start${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# Check if virtual environment exists
if [[ ! -d "venv" ]]; then
    echo -e "${RED}[✗] Virtual environment not found${NC}"
    echo -e "${YELLOW}Please run ./install.sh first${NC}"
    exit 1
fi

# Check if .env file exists
if [[ ! -f ".env" ]]; then
    echo -e "${RED}[✗] .env file not found${NC}"
    echo -e "${YELLOW}Please run ./install.sh first${NC}"
    exit 1
fi

# Check if PostgreSQL container is running
CONTAINER_NAME="sapine-postgres-db"
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}[⚠] PostgreSQL container not running. Starting...${NC}"
    docker start ${CONTAINER_NAME} 2>/dev/null || {
        echo -e "${RED}[✗] Failed to start PostgreSQL container${NC}"
        echo -e "${YELLOW}Please run ./install.sh first${NC}"
        exit 1
    }
    echo -e "${GREEN}[✓] PostgreSQL container started${NC}"
    sleep 3
else
    echo -e "${GREEN}[✓] PostgreSQL container is running${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}[•] Activating virtual environment...${NC}"
source venv/bin/activate

# Get port from .env
API_PORT=$(grep "^PORT=" .env | cut -d'=' -f2)
API_PORT=${API_PORT:-8000}

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Starting FastAPI Server...${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}API Documentation:${NC} http://localhost:${API_PORT}/docs"
echo -e "${BLUE}Health Check:${NC}      http://localhost:${API_PORT}/health"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start the server
python -m app.main
