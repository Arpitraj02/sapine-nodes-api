#!/bin/bash

################################################################################
# Sapine Bot Hosting Platform - One-Click Setup Script for Ubuntu
# 
# This script provides a bulletproof installation that:
# - Checks all prerequisites and installs missing dependencies
# - Sets up PostgreSQL database in Docker
# - Creates and configures Python virtual environment
# - Generates secure credentials automatically
# - Validates the installation at each step
# - Provides clear error messages and recovery instructions
#
# Supported: Ubuntu 20.04+, Debian 11+
# Usage: ./install.sh
################################################################################

set -e  # Exit on any error

# Color codes for beautiful output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
POSTGRES_USER="sapine_user"
POSTGRES_PASSWORD=""  # Will be auto-generated
POSTGRES_DB="sapine_bots"
POSTGRES_PORT="5432"
API_PORT="8000"
BOT_STORAGE_PATH="./bot_storage"
CONTAINER_NAME="sapine-postgres-db"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}$1${NC}"
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════${NC}"
}

# Function to check if running on supported OS
check_os() {
    log_step "Step 1/10: Checking Operating System"
    
    if [[ ! -f /etc/os-release ]]; then
        log_error "Cannot determine OS. This script requires Ubuntu 20.04+ or Debian 11+"
        exit 1
    fi
    
    . /etc/os-release
    
    if [[ "$ID" == "ubuntu" ]]; then
        log_success "Ubuntu detected: $VERSION"
    elif [[ "$ID" == "debian" ]]; then
        log_success "Debian detected: $VERSION"
    else
        log_warning "OS: $ID $VERSION (not officially supported, but will try to continue)"
    fi
}

# Function to check and install Python
check_python() {
    log_step "Step 2/10: Checking Python Installation"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        log_success "Python 3 found: $PYTHON_VERSION"
        
        # Check if version is 3.8+
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8 ]]; then
            log_error "Python 3.8+ required, found $PYTHON_VERSION"
            log_info "Installing Python 3..."
            sudo apt-get update -qq
            sudo apt-get install -y python3 python3-pip python3-venv
        fi
    else
        log_warning "Python 3 not found. Installing..."
        sudo apt-get update -qq
        sudo apt-get install -y python3 python3-pip python3-venv
        log_success "Python 3 installed"
    fi
    
    # Verify pip
    if ! command -v pip3 &> /dev/null; then
        log_warning "pip3 not found. Installing..."
        sudo apt-get install -y python3-pip
    fi
    log_success "pip3 found: $(pip3 --version)"
}

# Function to check and install Docker
check_docker() {
    log_step "Step 3/10: Checking Docker Installation"
    
    if command -v docker &> /dev/null; then
        log_success "Docker found: $(docker --version)"
    else
        log_warning "Docker not found. Installing Docker..."
        
        # Install prerequisites
        sudo apt-get update -qq
        sudo apt-get install -y ca-certificates curl gnupg lsb-release
        
        # Add Docker's official GPG key
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        
        # Set up repository
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Install Docker
        sudo apt-get update -qq
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        
        # Add current user to docker group
        sudo usermod -aG docker $USER
        
        log_success "Docker installed successfully"
        log_warning "You may need to log out and back in for Docker group permissions to take effect"
    fi
    
    # Check if Docker daemon is running
    if ! sudo docker info &> /dev/null; then
        log_warning "Docker daemon not running. Starting..."
        sudo systemctl start docker
        sudo systemctl enable docker
        sleep 3
    fi
    
    if sudo docker info &> /dev/null; then
        log_success "Docker daemon is running"
    else
        log_error "Failed to start Docker daemon"
        exit 1
    fi
}

# Function to generate secure credentials
generate_credentials() {
    log_step "Step 4/10: Generating Secure Credentials"
    
    # Generate secure password for PostgreSQL
    if command -v openssl &> /dev/null; then
        POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        JWT_SECRET=$(openssl rand -hex 32)
    else
        POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(25))")
        JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    fi
    
    log_success "PostgreSQL password generated"
    log_success "JWT secret generated"
}

# Function to setup PostgreSQL
setup_postgres() {
    log_step "Step 5/10: Setting up PostgreSQL Database"
    
    # Check if container already exists
    if sudo docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_warning "Existing PostgreSQL container found"
        read -p "Do you want to remove it and create a new one? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Stopping and removing existing container..."
            sudo docker stop ${CONTAINER_NAME} 2>/dev/null || true
            sudo docker rm ${CONTAINER_NAME} 2>/dev/null || true
            sudo docker volume rm sapine-postgres-data 2>/dev/null || true
        else
            log_info "Using existing PostgreSQL container"
            sudo docker start ${CONTAINER_NAME} 2>/dev/null || true
            POSTGRES_PASSWORD="dev_password_123"  # Use existing password
            log_warning "Using default password. Check your .env file for credentials."
        fi
    fi
    
    # Start new container if needed
    if ! sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_info "Creating PostgreSQL container..."
        sudo docker run -d \
            --name ${CONTAINER_NAME} \
            -e POSTGRES_USER=${POSTGRES_USER} \
            -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
            -e POSTGRES_DB=${POSTGRES_DB} \
            -p ${POSTGRES_PORT}:5432 \
            -v sapine-postgres-data:/var/lib/postgresql/data \
            --restart unless-stopped \
            postgres:15-alpine
        
        log_success "PostgreSQL container created"
    fi
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if sudo docker exec ${CONTAINER_NAME} pg_isready -U ${POSTGRES_USER} &> /dev/null; then
            log_success "PostgreSQL is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "PostgreSQL failed to start"
            sudo docker logs ${CONTAINER_NAME}
            exit 1
        fi
        sleep 2
    done
}

# Function to create .env file
create_env_file() {
    log_step "Step 6/10: Creating Environment Configuration"
    
    if [[ -f .env ]]; then
        log_warning ".env file already exists"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing .env file"
            return
        fi
    fi
    
    cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}

# JWT Authentication
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Bot Storage
BOT_STORAGE_PATH=${BOT_STORAGE_PATH}

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Server Configuration
HOST=0.0.0.0
PORT=${API_PORT}

# Docker Compose Configuration
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_PORT=${POSTGRES_PORT}
API_PORT=${API_PORT}
EOF
    
    chmod 600 .env
    log_success ".env file created with secure permissions"
}

# Function to create bot storage directory
create_bot_storage() {
    log_step "Step 7/10: Creating Bot Storage Directory"
    
    if [[ ! -d "$BOT_STORAGE_PATH" ]]; then
        mkdir -p "$BOT_STORAGE_PATH"
        log_success "Bot storage directory created: $BOT_STORAGE_PATH"
    else
        log_success "Bot storage directory exists: $BOT_STORAGE_PATH"
    fi
    
    # Set proper permissions
    chmod 755 "$BOT_STORAGE_PATH"
}

# Function to setup Python virtual environment
setup_venv() {
    log_step "Step 8/10: Setting up Python Virtual Environment"
    
    if [[ -d venv ]]; then
        log_info "Virtual environment exists"
    else
        log_info "Creating virtual environment..."
        python3 -m venv venv
        log_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    log_info "Upgrading pip..."
    pip install --upgrade pip --quiet
    
    log_info "Installing Python dependencies (this may take a few minutes)..."
    pip install -r requirements.txt --quiet
    
    log_success "All Python dependencies installed"
}

# Function to initialize database
init_database() {
    log_step "Step 9/10: Initializing Database"
    
    source venv/bin/activate
    
    log_info "Testing database connection..."
    python3 << 'EOF'
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        print(f"✓ Database connection successful")
        for row in result:
            print(f"  PostgreSQL version: {row[0].split(',')[0]}")
except Exception as e:
    print(f"✗ Database connection failed: {e}")
    exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        log_success "Database connection verified"
    else
        log_error "Database connection failed"
        exit 1
    fi
    
    log_info "Database tables will be created on first API startup"
}

# Function to verify installation
verify_installation() {
    log_step "Step 10/10: Verifying Installation"
    
    # Check Python packages
    log_info "Checking installed packages..."
    source venv/bin/activate
    
    REQUIRED_PACKAGES=("fastapi" "uvicorn" "sqlalchemy" "pydantic" "email-validator" "docker")
    ALL_OK=true
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if pip show "$package" &> /dev/null; then
            log_success "  ✓ $package"
        else
            log_error "  ✗ $package (missing)"
            ALL_OK=false
        fi
    done
    
    if [ "$ALL_OK" = true ]; then
        log_success "All required packages installed"
    else
        log_error "Some packages are missing"
        exit 1
    fi
    
    # Check Docker
    if sudo docker ps | grep -q ${CONTAINER_NAME}; then
        log_success "PostgreSQL container is running"
    else
        log_error "PostgreSQL container is not running"
        exit 1
    fi
    
    # Check .env file
    if [[ -f .env ]]; then
        log_success ".env file exists"
    else
        log_error ".env file missing"
        exit 1
    fi
}

# Function to display completion message
show_completion() {
    echo ""
    echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║                                                               ║${NC}"
    echo -e "${GREEN}${BOLD}║  🎉  Installation Complete!  🎉                               ║${NC}"
    echo -e "${GREEN}${BOLD}║                                                               ║${NC}"
    echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}${BOLD}Quick Start:${NC}"
    echo -e "  ${YELLOW}1.${NC} Activate virtual environment:"
    echo -e "     ${GREEN}source venv/bin/activate${NC}"
    echo ""
    echo -e "  ${YELLOW}2.${NC} Start the API server:"
    echo -e "     ${GREEN}python -m app.main${NC}"
    echo ""
    echo -e "  ${YELLOW}3.${NC} Open your browser and visit:"
    echo -e "     ${GREEN}http://localhost:${API_PORT}/docs${NC}"
    echo ""
    echo -e "${CYAN}${BOLD}Database Information:${NC}"
    echo -e "  ${BLUE}Container:${NC} ${CONTAINER_NAME}"
    echo -e "  ${BLUE}Database:${NC} ${POSTGRES_DB}"
    echo -e "  ${BLUE}Username:${NC} ${POSTGRES_USER}"
    echo -e "  ${BLUE}Password:${NC} ${POSTGRES_PASSWORD}"
    echo -e "  ${BLUE}Port:${NC} ${POSTGRES_PORT}"
    echo ""
    echo -e "${CYAN}${BOLD}Useful Commands:${NC}"
    echo -e "  ${BLUE}Start API:${NC}        source venv/bin/activate && python -m app.main"
    echo -e "  ${BLUE}Stop API:${NC}         Press Ctrl+C"
    echo -e "  ${BLUE}View DB:${NC}          sudo docker exec -it ${CONTAINER_NAME} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}"
    echo -e "  ${BLUE}Stop Database:${NC}    sudo docker stop ${CONTAINER_NAME}"
    echo -e "  ${BLUE}Start Database:${NC}   sudo docker start ${CONTAINER_NAME}"
    echo -e "  ${BLUE}View DB Logs:${NC}     sudo docker logs ${CONTAINER_NAME}"
    echo ""
    echo -e "${CYAN}${BOLD}Docker Compose (Alternative):${NC}"
    echo -e "  ${BLUE}Start all:${NC}        docker-compose up -d"
    echo -e "  ${BLUE}Stop all:${NC}         docker-compose down"
    echo -e "  ${BLUE}View logs:${NC}        docker-compose logs -f"
    echo ""
    echo -e "${YELLOW}${BOLD}Note:${NC} Your credentials are saved in the ${GREEN}.env${NC} file"
    echo -e "${YELLOW}${BOLD}Security:${NC} Do not commit the ${GREEN}.env${NC} file to version control"
    echo ""
}

# Main execution
main() {
    clear
    echo -e "${MAGENTA}${BOLD}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ███████╗ █████╗ ██████╗ ██╗███╗   ██╗███████╗                  ║
║   ██╔════╝██╔══██╗██╔══██╗██║████╗  ██║██╔════╝                  ║
║   ███████╗███████║██████╔╝██║██╔██╗ ██║█████╗                    ║
║   ╚════██║██╔══██║██╔═══╝ ██║██║╚██╗██║██╔══╝                    ║
║   ███████║██║  ██║██║     ██║██║ ╚████║███████╗                  ║
║   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═══╝╚══════╝                  ║
║                                                                   ║
║              Bot Hosting Platform - Setup Script                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    log_info "Starting bulletproof installation for Ubuntu..."
    log_info "This will take a few minutes..."
    echo ""
    
    # Execute all steps
    check_os
    check_python
    check_docker
    generate_credentials
    setup_postgres
    create_env_file
    create_bot_storage
    setup_venv
    init_database
    verify_installation
    
    # Show completion message
    show_completion
}

# Run main function
main
