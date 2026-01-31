# Deployment Guide for Ubuntu VPS

This guide provides step-by-step instructions for deploying the Sapine Bot Hosting Platform on a generic Ubuntu VPS (20.04 LTS or 22.04 LTS).

## Prerequisites

- Ubuntu 20.04 LTS or 22.04 LTS VPS
- SSH access with sudo privileges
- At least 2GB RAM, 2 CPU cores, 20GB storage
- A domain name (optional, for HTTPS)
- Public IP address

## Table of Contents

1. [Initial Server Setup](#1-initial-server-setup)
2. [Install Dependencies](#2-install-dependencies)
3. [Install Docker and Docker Compose](#3-install-docker-and-docker-compose)
4. [Clone Repository](#4-clone-repository)
5. [Configure Environment](#5-configure-environment)
6. [Set Up PostgreSQL](#6-set-up-postgresql)
7. [Deploy Application](#7-deploy-application)
8. [Configure Firewall](#8-configure-firewall)
9. [Set Up Systemd Service](#9-set-up-systemd-service)
10. [SSL/TLS with Let's Encrypt](#10-ssltls-with-lets-encrypt)
11. [Monitoring and Maintenance](#11-monitoring-and-maintenance)

---

## 1. Initial Server Setup

### Connect to Your VPS

```bash
ssh root@your-vps-ip
# or
ssh ubuntu@your-vps-ip
```

### Update System Packages

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### Create a Deployment User (Optional but Recommended)

```bash
# Create user
sudo adduser sapine

# Add user to sudo group
sudo usermod -aG sudo sapine

# Switch to new user
su - sapine
```

### Set Up SSH Key Authentication (Recommended)

On your local machine:
```bash
ssh-copy-id sapine@your-vps-ip
```

### Configure Timezone

```bash
sudo timedatectl set-timezone UTC
# or your preferred timezone:
# sudo timedatectl set-timezone America/New_York
```

---

## 2. Install Dependencies

### Install Python 3.11

Ubuntu 22.04 comes with Python 3.10. For Python 3.11:

```bash
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
```

Verify installation:
```bash
python3.11 --version
```

### Install Essential Build Tools

```bash
sudo apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    curl \
    wget \
    unzip \
    vim \
    htop
```

---

## 3. Install Docker and Docker Compose

### Install Docker

```bash
# Remove old versions
sudo apt-get remove -y docker docker-engine docker.io containerd runc

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Enable and start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Verify installation
docker --version
```

**Important:** Log out and back in for group changes to take effect.

### Install Docker Compose

```bash
# Download latest version
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

### Test Docker

```bash
# Test Docker (should run without sudo)
docker run hello-world

# If you get permission errors, log out and back in
```

---

## 4. Clone Repository

### Create Application Directory

```bash
sudo mkdir -p /opt/sapine
sudo chown $USER:$USER /opt/sapine
cd /opt/sapine
```

### Clone the Repository

```bash
git clone https://github.com/Arpitraj02/sapine-nodes-api.git
cd sapine-nodes-api
```

---

## 5. Configure Environment

### Generate Secure JWT Secret

```bash
# Generate a secure 64-character random secret
openssl rand -hex 32
```

Save this secret - you'll need it in the next step.

### Create Production .env File

```bash
# Create .env file
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://sapine_prod:CHANGE_THIS_PASSWORD@localhost:5432/sapine_bots_prod

# JWT Secret (REQUIRED - use the generated secret from above)
JWT_SECRET_KEY=PASTE_YOUR_GENERATED_SECRET_HERE
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Bot Storage
BOT_STORAGE_PATH=/var/lib/bots

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Server
HOST=0.0.0.0
PORT=8000

# Docker Compose
POSTGRES_PASSWORD=CHANGE_THIS_PASSWORD
POSTGRES_PORT=5432
API_PORT=8000
EOF
```

### Edit .env with Production Values

```bash
vim .env
```

**Required changes:**
1. Replace `CHANGE_THIS_PASSWORD` with a strong database password
2. Replace `PASTE_YOUR_GENERATED_SECRET_HERE` with the JWT secret you generated
3. Optionally change the `API_PORT` if needed

**Security Notes:**
- Use strong, unique passwords
- Never commit .env to version control
- Keep the JWT secret safe and confidential

### Create Bot Storage Directory

```bash
sudo mkdir -p /var/lib/bots
sudo chown -R $USER:$USER /var/lib/bots
sudo chmod 755 /var/lib/bots
```

---

## 6. Set Up PostgreSQL

### Option A: Using Docker Compose (Recommended)

The included `docker-compose.yml` will set up PostgreSQL automatically.

```bash
# Start only PostgreSQL
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 10

# Verify PostgreSQL is running
docker-compose ps
docker-compose logs postgres
```

### Option B: Using System PostgreSQL

If you prefer system PostgreSQL:

```bash
# Install PostgreSQL
sudo apt-get install -y postgresql postgresql-contrib

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database user and database
sudo -u postgres psql << EOF
CREATE USER sapine_prod WITH PASSWORD 'your_secure_password';
CREATE DATABASE sapine_bots_prod OWNER sapine_prod;
GRANT ALL PRIVILEGES ON DATABASE sapine_bots_prod TO sapine_prod;
\q
EOF

# Update DATABASE_URL in .env to use system PostgreSQL
# DATABASE_URL=postgresql://sapine_prod:your_secure_password@localhost:5432/sapine_bots_prod
```

---

## 7. Deploy Application

### Option A: Deploy with Docker Compose (Recommended)

This will deploy both the API and PostgreSQL in containers:

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

The API will be available at `http://your-vps-ip:8000`

### Option B: Deploy with Systemd (Direct Python)

For running the API directly on the host:

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Test the application
python -m app.main
```

Press `Ctrl+C` to stop, then continue to set up systemd service in the next section.

### Verify Deployment

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","service":"sapine-bot-hosting"}
```

---

## 8. Configure Firewall

### Install and Configure UFW (Uncomplicated Firewall)

```bash
# Install UFW if not installed
sudo apt-get install -y ufw

# Allow SSH (CRITICAL - do this first!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow API port (if exposing directly, otherwise skip)
sudo ufw allow 8000/tcp

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status verbose
```

**Security Best Practices:**

1. **Don't expose port 8000 directly in production** - use a reverse proxy (nginx/Caddy)
2. **Only allow port 5432 (PostgreSQL) from localhost** (default behavior)
3. **Keep SSH enabled** on port 22 or a custom port
4. **Consider changing default SSH port** for added security

### Advanced: Change SSH Port (Optional)

```bash
# Edit SSH config
sudo vim /etc/ssh/sshd_config

# Change line:
# Port 22
# to:
# Port 2222

# Save and restart SSH
sudo systemctl restart sshd

# Update firewall
sudo ufw allow 2222/tcp
sudo ufw delete allow 22/tcp
```

---

## 9. Set Up Systemd Service

This section applies if you're running the API directly (not using Docker Compose for the API).

### Create Systemd Service File

```bash
sudo tee /etc/systemd/system/sapine-api.service > /dev/null << 'EOF'
[Unit]
Description=Sapine Bot Hosting Platform API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=sapine
Group=sapine
WorkingDirectory=/opt/sapine/sapine-nodes-api
Environment="PATH=/opt/sapine/sapine-nodes-api/venv/bin"
EnvironmentFile=/opt/sapine/sapine-nodes-api/.env
ExecStart=/opt/sapine/sapine-nodes-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/bots /var/run/docker.sock

[Install]
WantedBy=multi-user.target
EOF
```

**Note:** Adjust paths if you used a different installation directory or user.

### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable sapine-api

# Start service
sudo systemctl start sapine-api

# Check status
sudo systemctl status sapine-api

# View logs
sudo journalctl -u sapine-api -f
```

### Service Management Commands

```bash
# Stop service
sudo systemctl stop sapine-api

# Restart service
sudo systemctl restart sapine-api

# View logs
sudo journalctl -u sapine-api -n 100 --no-pager

# Follow logs in real-time
sudo journalctl -u sapine-api -f
```

---

## 10. SSL/TLS with Let's Encrypt

### Install Nginx as Reverse Proxy

```bash
sudo apt-get install -y nginx
```

### Configure Nginx

```bash
# Create nginx config
sudo tee /etc/nginx/sites-available/sapine-api > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # WebSocket support
        proxy_read_timeout 86400;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/sapine-api /etc/nginx/sites-enabled/

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

**Important:** Replace `your-domain.com` with your actual domain.

### Install Certbot for SSL

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow the prompts:
# 1. Enter your email address
# 2. Agree to terms of service
# 3. Choose whether to redirect HTTP to HTTPS (recommended: yes)

# Test auto-renewal
sudo certbot renew --dry-run
```

### Update Firewall for Nginx

```bash
# If exposing via nginx, remove direct API port access
sudo ufw delete allow 8000/tcp

# Allow Nginx
sudo ufw allow 'Nginx Full'

# Verify
sudo ufw status
```

Your API is now available at `https://your-domain.com`

---

## 11. Monitoring and Maintenance

### Set Up Log Rotation

```bash
# Create logrotate config
sudo tee /etc/logrotate.d/sapine-api > /dev/null << 'EOF'
/var/log/sapine/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 sapine sapine
    sharedscripts
    postrotate
        systemctl reload sapine-api > /dev/null 2>&1 || true
    endscript
}
EOF

# Create log directory
sudo mkdir -p /var/log/sapine
sudo chown sapine:sapine /var/log/sapine
```

### Monitor Resource Usage

```bash
# Check CPU and memory
htop

# Check disk usage
df -h

# Check Docker containers
docker ps
docker stats

# View application logs
sudo journalctl -u sapine-api -f

# View Docker Compose logs
cd /opt/sapine/sapine-nodes-api
docker-compose logs -f
```

### Database Backup

Create a backup script:

```bash
# Create backup script
sudo tee /opt/sapine/backup-db.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/sapine/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="sapine_bots_prod"
DB_USER="sapine_prod"

mkdir -p $BACKUP_DIR

# If using Docker Compose PostgreSQL:
docker exec sapine-db pg_dump -U sapine -d sapine_bots > $BACKUP_DIR/backup_$DATE.sql

# If using system PostgreSQL:
# sudo -u postgres pg_dump $DB_NAME > $BACKUP_DIR/backup_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/backup_$DATE.sql"
EOF

# Make executable
sudo chmod +x /opt/sapine/backup-db.sh
```

Set up daily backup with cron:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/sapine/backup-db.sh >> /var/log/sapine/backup.log 2>&1
```

### Update Application

```bash
cd /opt/sapine/sapine-nodes-api

# Pull latest changes
git pull origin main

# If using Docker Compose:
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# If using systemd:
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sapine-api
```

### Security Updates

```bash
# Regularly update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Update Docker images
docker-compose pull
docker-compose up -d

# Check for security vulnerabilities
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## Troubleshooting

### API Not Accessible

```bash
# Check if service is running
sudo systemctl status sapine-api
# or
docker-compose ps

# Check logs
sudo journalctl -u sapine-api -n 50
# or
docker-compose logs api

# Check if port is listening
sudo netstat -tulpn | grep 8000

# Test locally
curl http://localhost:8000/health
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql
# or
docker-compose ps postgres

# Test database connection
psql postgresql://sapine_prod:password@localhost:5432/sapine_bots_prod
# or
docker exec -it sapine-db psql -U sapine -d sapine_bots

# Check database logs
docker-compose logs postgres
```

### Docker Issues

```bash
# Check Docker daemon
sudo systemctl status docker

# Check Docker containers
docker ps -a

# View container logs
docker logs sapine-api
docker logs sapine-db

# Restart containers
docker-compose restart

# Full reset (WARNING: destroys data)
docker-compose down -v
docker-compose up -d
```

### Port Already in Use

```bash
# Find what's using the port
sudo lsof -i :8000

# Kill the process
sudo kill -9 <PID>
```

---

## Production Checklist

Before going live:

- [ ] Strong, unique passwords for database and JWT secret
- [ ] Firewall configured (UFW or iptables)
- [ ] SSL/TLS certificate installed (Let's Encrypt)
- [ ] Nginx reverse proxy configured
- [ ] Systemd service or Docker Compose running
- [ ] Database backups scheduled
- [ ] Log rotation configured
- [ ] Monitoring set up
- [ ] Security updates enabled
- [ ] .env file secured (600 permissions)
- [ ] Regular maintenance scheduled
- [ ] Documentation reviewed
- [ ] Test all endpoints work
- [ ] WebSocket connections work
- [ ] Bot creation and execution tested

---

## Additional Security Hardening

### Fail2Ban for SSH Protection

```bash
# Install Fail2Ban
sudo apt-get install -y fail2ban

# Configure
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Edit configuration
sudo vim /etc/fail2ban/jail.local
# Set: bantime = 1h, maxretry = 3

# Start service
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Check status
sudo fail2ban-client status sshd
```

### Disable Root Login

```bash
# Edit SSH config
sudo vim /etc/ssh/sshd_config

# Set:
# PermitRootLogin no
# PasswordAuthentication no  # If using SSH keys

# Restart SSH
sudo systemctl restart sshd
```

### Regular Security Scans

```bash
# Install security tools
sudo apt-get install -y lynis rkhunter

# Run security audit
sudo lynis audit system

# Scan for rootkits
sudo rkhunter --check
```

---

## Support and Resources

- **Repository:** https://github.com/Arpitraj02/sapine-nodes-api
- **API Documentation:** https://your-domain.com/docs
- **Issues:** https://github.com/Arpitraj02/sapine-nodes-api/issues

For additional help, please refer to:
- [README.md](README.md) - Project overview
- [API_TESTING.md](API_TESTING.md) - API testing guide
- [Testing.txt](Testing.txt) - cURL testing examples
- [SECURITY.md](SECURITY.md) - Security guidelines

---

## Quick Reference Commands

```bash
# Service management
sudo systemctl start sapine-api
sudo systemctl stop sapine-api
sudo systemctl restart sapine-api
sudo systemctl status sapine-api

# Docker Compose
docker-compose up -d
docker-compose down
docker-compose logs -f
docker-compose ps

# View logs
sudo journalctl -u sapine-api -f
docker-compose logs -f api

# Database access
docker exec -it sapine-db psql -U sapine -d sapine_bots

# Check health
curl http://localhost:8000/health

# Update application
cd /opt/sapine/sapine-nodes-api
git pull
docker-compose up -d --build
```

---

**Congratulations!** Your Sapine Bot Hosting Platform is now deployed and ready for production use.
