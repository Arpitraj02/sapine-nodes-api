# Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User/Client                              │
│                    (Browser, curl, etc.)                         │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ HTTP/HTTPS & WebSocket
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│                      FastAPI Application                         │
│                        (app/main.py)                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Authentication (app/auth.py)                             │  │
│  │  - JWT Token Generation/Validation                        │  │
│  │  - Role-Based Access Control (RBAC)                       │  │
│  │  - Password Hashing (Argon2)                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Bot Management (app/bots.py)                             │  │
│  │  - CRUD Operations                                        │  │
│  │  - File Upload Handler                                    │  │
│  │  - Ownership Verification                                 │  │
│  │  - Container Lifecycle                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  WebSocket Streaming (app/sockets.py)                     │  │
│  │  - Real-time Log Streaming                                │  │
│  │  - Authentication & Authorization                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Utilities (app/utils.py)                                 │  │
│  │  - Input Validation                                       │  │
│  │  - Rate Limiting                                          │  │
│  │  - Error Handling                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────┬───────────────────┬────────────────────────┬─┘
                   │                   │                        │
                   │                   │                        │
      ┌────────────▼──────┐  ┌─────────▼──────────┐  ┌────────▼────────┐
      │  Database Layer   │  │  Docker Engine     │  │  File Storage   │
      │   (app/db.py)     │  │  (app/docker.py)   │  │  (/var/lib/bots)│
      │                   │  │                    │  │                 │
      │  SQLAlchemy       │  │  Container Mgmt    │  │  Bot Code Files │
      │  Session Mgmt     │  │  Security Layer    │  │  Dependencies   │
      └─────────┬─────────┘  └─────────┬──────────┘  └─────────────────┘
                │                      │
                │                      │
      ┌─────────▼─────────┐  ┌─────────▼──────────────────────────────┐
      │   PostgreSQL      │  │      Docker Containers                 │
      │   Database        │  │  ┌──────────────────────────────────┐  │
      │                   │  │  │  Bot Container 1 (Python)        │  │
      │  ┌─────────────┐  │  │  │  - No Privileged Mode            │  │
      │  │ Users       │  │  │  │  - All Capabilities Dropped      │  │
      │  │ Plans       │  │  │  │  - CPU/RAM Limits                │  │
      │  │ Bots        │  │  │  │  - Network Isolation             │  │
      │  │ AuditLogs   │  │  │  └──────────────────────────────────┘  │
      │  └─────────────┘  │  │  ┌──────────────────────────────────┐  │
      └───────────────────┘  │  │  Bot Container 2 (Node.js)       │  │
                             │  │  - No Privileged Mode            │  │
                             │  │  - All Capabilities Dropped      │  │
                             │  │  - CPU/RAM Limits                │  │
                             │  │  - Network Isolation             │  │
                             │  └──────────────────────────────────┘  │
                             └─────────────────────────────────────────┘
```

## Request Flow

### 1. User Registration/Login
```
Client → POST /auth/register → auth.py (hash password)
                             → models.py (create User)
                             → db.py (save to PostgreSQL)
                             → auth.py (generate JWT)
                             → Client (return token)
```

### 2. Bot Creation
```
Client → POST /bots → auth.py (verify JWT + ownership)
                    → bots.py (validate input)
                    → models.py (create Bot)
                    → db.py (save to PostgreSQL)
                    → utils.py (create storage directory)
                    → Client (return bot info)
```

### 3. File Upload
```
Client → POST /bots/{id}/upload → auth.py (verify JWT + ownership)
                                 → bots.py (verify ownership)
                                 → utils.py (sanitize filename)
                                 → File Storage (extract files)
                                 → db.py (update Bot)
                                 → Client (success)
```

### 4. Bot Start
```
Client → POST /bots/{id}/start → auth.py (verify JWT + ownership)
                                → bots.py (verify ownership)
                                → docker.py (create container if needed)
                                → Docker Engine (start container)
                                → db.py (update Bot status)
                                → Client (return status)
```

### 5. Log Streaming
```
Client → WS /bots/{id}/logs?token=JWT → sockets.py (verify JWT)
                                      → bots.py (verify ownership)
                                      → docker.py (stream logs)
                                      → Docker Engine (read container logs)
                                      → Client (real-time logs)
```

## Security Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: API Security                                           │
│  - JWT Authentication                                            │
│  - RBAC (USER, ADMIN, OWNER)                                     │
│  - Rate Limiting (60 req/min)                                    │
│  - Input Validation                                              │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: Application Security                                   │
│  - Command Validation (no shell injection)                       │
│  - Path Sanitization (no traversal)                              │
│  - Ownership Checks (users access only their bots)               │
│  - Audit Logging (all sensitive actions)                         │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: Container Security                                     │
│  - No Privileged Mode (privileged=False)                         │
│  - All Capabilities Dropped (cap_drop=["ALL"])                   │
│  - Resource Limits (CPU + RAM)                                   │
│  - Network Isolation (bridge mode)                               │
│  - Security Options (no-new-privileges)                          │
│  - Container ID Hidden (internal only)                           │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: Database Security                                      │
│  - Parameterized Queries (ORM)                                   │
│  - Password Hashing (Argon2)                                     │
│  - Connection Pooling                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: Bot Lifecycle

```
CREATED → RUNNING → STOPPED → RUNNING → CRASHED
   ↑                                        │
   └────────────────────────────────────────┘
                  (recreate)

States:
- CREATED: Bot exists in DB, no container
- RUNNING: Container running
- STOPPED: Container stopped by user
- CRASHED: Container exited with error

Transitions:
- CREATED → RUNNING: User starts bot (POST /bots/{id}/start)
- RUNNING → STOPPED: User stops bot (POST /bots/{id}/stop)
- STOPPED → RUNNING: User restarts bot (POST /bots/{id}/restart)
- RUNNING → CRASHED: Container exits with non-zero code
- ANY → DELETED: User deletes bot (DELETE /bots/{id})
```

## Module Dependencies

```
main.py
  ├── auth.py
  │   ├── db.py
  │   │   └── models.py
  │   └── utils.py
  ├── bots.py
  │   ├── auth.py (verified ownership)
  │   ├── db.py
  │   ├── models.py
  │   ├── docker.py
  │   │   └── utils.py
  │   └── utils.py
  └── sockets.py
      ├── auth.py
      ├── bots.py
      ├── db.py
      ├── models.py
      └── docker.py
```

## File Organization

```
sapine-nodes-api/
│
├── Core Application (1,822 lines)
│   ├── app/__init__.py       (136 chars)
│   ├── app/main.py          (10,395 chars) - FastAPI app
│   ├── app/auth.py          (4,155 chars)  - Authentication
│   ├── app/db.py            (1,526 chars)  - Database
│   ├── app/models.py        (4,297 chars)  - Models
│   ├── app/docker.py        (10,206 chars) - Docker layer
│   ├── app/bots.py          (14,228 chars) - Bot logic
│   ├── app/sockets.py       (3,408 chars)  - WebSocket
│   └── app/utils.py         (5,587 chars)  - Utilities
│
├── Configuration
│   ├── requirements.txt      - Python dependencies
│   ├── .env.example          - Environment template
│   ├── .gitignore            - Git ignore rules
│   ├── Dockerfile            - Container build
│   ├── docker-compose.yml    - Deployment config
│   └── setup.sh              - Setup automation
│
├── Documentation (37KB+)
│   ├── README.md             - Main documentation
│   ├── API_TESTING.md        - Testing guide
│   ├── SECURITY.md           - Security docs
│   └── PROJECT_SUMMARY.md    - Implementation overview
│
└── Examples
    ├── examples/README.md     - Examples guide
    ├── examples/python/       - Python bot examples
    │   ├── simple_bot.py
    │   ├── bot_with_dependencies.py
    │   └── requirements.txt
    └── examples/nodejs/       - Node.js bot examples
        ├── simple_bot.js
        ├── bot_with_dependencies.js
        └── package.json
```

## Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│  Language: Python 3.11+                                      │
│  Framework: FastAPI 0.109.0                                  │
│  Database: PostgreSQL (via SQLAlchemy 2.0.25)               │
│  Container: Docker (via docker-py 7.0.0)                     │
│  Auth: JWT (via python-jose 3.3.0)                           │
│  Password: Argon2 (via argon2-cffi 23.1.0 + passlib 1.7.4)  │
│  WebSocket: FastAPI native + websockets 12.0                 │
│  Server: Uvicorn 0.27.0                                      │
└─────────────────────────────────────────────────────────────┘
```

## Performance Characteristics

- **Request Latency**: <50ms (typical)
- **WebSocket Latency**: <10ms (log streaming)
- **Container Start**: 2-5s (Python), 1-3s (Node.js)
- **Max Concurrent Users**: Limited by database connections (20)
- **Rate Limit**: 60 req/min per IP (configurable)
- **Memory per Bot**: 256MB-1GB (plan-dependent)
- **CPU per Bot**: 0.5-2.0 cores (plan-dependent)
