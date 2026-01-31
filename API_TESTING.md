# API Testing Guide

This document provides examples for testing all API endpoints.

## Prerequisites

- Server running at `http://localhost:8000`
- `curl` or similar HTTP client
- PostgreSQL database running

## 1. Health Check

Test if the server is running:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "sapine-bot-hosting"
}
```

## 2. User Registration

Register a new user:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123"
  }'
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Save the `access_token` for subsequent requests.

## 3. User Login

Login with existing credentials:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123"
  }'
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## 4. Get Current User Info

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response:
```json
{
  "id": 1,
  "email": "user@example.com",
  "role": "USER",
  "status": "ACTIVE",
  "created_at": "2024-01-31T10:00:00"
}
```

## 5. Create a Bot

Create a new Python bot:

```bash
curl -X POST http://localhost:8000/bots \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-discord-bot",
    "runtime": "python",
    "start_cmd": "python bot.py",
    "plan_id": 1
  }'
```

Expected response:
```json
{
  "id": 1,
  "name": "my-discord-bot",
  "runtime": "python",
  "status": "CREATED",
  "start_cmd": "python bot.py",
  "source_type": null,
  "created_at": "2024-01-31T10:05:00"
}
```

Create a Node.js bot:

```bash
curl -X POST http://localhost:8000/bots \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-telegram-bot",
    "runtime": "node",
    "start_cmd": "node index.js",
    "plan_id": 1
  }'
```

## 6. List User's Bots

```bash
curl http://localhost:8000/bots \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response:
```json
{
  "bots": [
    {
      "id": 1,
      "name": "my-discord-bot",
      "runtime": "python",
      "status": "CREATED",
      "start_cmd": "python bot.py",
      "source_type": null,
      "created_at": "2024-01-31T10:05:00"
    }
  ],
  "total": 1
}
```

## 7. Upload Bot Code

### Upload a Single File

Create a simple Python bot file:

```bash
echo 'print("Hello from bot!")' > bot.py
```

Upload it:

```bash
curl -X POST http://localhost:8000/bots/1/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@bot.py"
```

Expected response:
```json
{
  "message": "Files uploaded successfully",
  "filename": "bot.py"
}
```

### Upload a ZIP Archive

Create a bot with dependencies:

```bash
# Create bot files
mkdir my-bot
cd my-bot

# Main bot file
cat > main.py << EOF
import requests
print("Bot starting...")
print("Bot running!")
EOF

# Requirements file
cat > requirements.txt << EOF
requests==2.31.0
EOF

# Create zip
zip -r bot.zip main.py requirements.txt
cd ..
```

Upload the zip:

```bash
curl -X POST http://localhost:8000/bots/1/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@my-bot/bot.zip"
```

## 8. Start a Bot

```bash
curl -X POST http://localhost:8000/bots/1/start \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response:
```json
{
  "id": 1,
  "name": "my-discord-bot",
  "runtime": "python",
  "status": "RUNNING",
  "start_cmd": "python bot.py",
  "source_type": "zip",
  "created_at": "2024-01-31T10:05:00"
}
```

## 9. Stop a Bot

```bash
curl -X POST http://localhost:8000/bots/1/stop \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response:
```json
{
  "id": 1,
  "name": "my-discord-bot",
  "runtime": "python",
  "status": "STOPPED",
  "start_cmd": "python bot.py",
  "source_type": "zip",
  "created_at": "2024-01-31T10:05:00"
}
```

## 10. Restart a Bot

```bash
curl -X POST http://localhost:8000/bots/1/restart \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response:
```json
{
  "id": 1,
  "name": "my-discord-bot",
  "runtime": "python",
  "status": "RUNNING",
  "start_cmd": "python bot.py",
  "source_type": "zip",
  "created_at": "2024-01-31T10:05:00"
}
```

## 11. Delete a Bot

```bash
curl -X DELETE http://localhost:8000/bots/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response: 204 No Content

## 12. Stream Bot Logs (WebSocket)

### Using JavaScript (Browser/Node.js)

```javascript
const token = "YOUR_TOKEN";
const botId = 1;
const ws = new WebSocket(`ws://localhost:8000/bots/${botId}/logs?token=${token}`);

ws.onopen = () => {
  console.log('Connected to bot logs');
};

ws.onmessage = (event) => {
  console.log('Log:', event.data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from bot logs');
};
```

### Using Python

```python
import asyncio
import websockets

async def stream_logs():
    token = "YOUR_TOKEN"
    bot_id = 1
    uri = f"ws://localhost:8000/bots/{bot_id}/logs?token={token}"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to bot logs")
        async for message in websocket:
            print(f"Log: {message}")

asyncio.run(stream_logs())
```

### Using wscat (CLI tool)

```bash
# Install wscat: npm install -g wscat
wscat -c "ws://localhost:8000/bots/1/logs?token=YOUR_TOKEN"
```

## 13. Admin Endpoints

### List All Users (Admin/Owner only)

```bash
curl http://localhost:8000/admin/users \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

Expected response:
```json
{
  "users": [
    {
      "id": 1,
      "email": "user@example.com",
      "role": "USER",
      "status": "ACTIVE",
      "created_at": "2024-01-31T10:00:00"
    },
    {
      "id": 2,
      "email": "admin@example.com",
      "role": "ADMIN",
      "status": "ACTIVE",
      "created_at": "2024-01-31T09:00:00"
    }
  ],
  "total": 2
}
```

### Suspend a User

```bash
curl -X POST http://localhost:8000/admin/users/1/suspend \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

Expected response:
```json
{
  "message": "User user@example.com has been suspended"
}
```

### Activate a User

```bash
curl -X POST http://localhost:8000/admin/users/1/activate \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

Expected response:
```json
{
  "message": "User user@example.com has been activated"
}
```

## Testing Complete Workflow

Here's a complete workflow script:

```bash
#!/bin/bash

API_URL="http://localhost:8000"

# 1. Register user
echo "1. Registering user..."
RESPONSE=$(curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123"
  }')

TOKEN=$(echo $RESPONSE | jq -r '.access_token')
echo "Token: $TOKEN"

# 2. Create bot
echo -e "\n2. Creating bot..."
BOT_RESPONSE=$(curl -s -X POST $API_URL/bots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-bot",
    "runtime": "python",
    "start_cmd": "python main.py",
    "plan_id": 1
  }')

BOT_ID=$(echo $BOT_RESPONSE | jq -r '.id')
echo "Bot ID: $BOT_ID"

# 3. Create and upload bot code
echo -e "\n3. Uploading bot code..."
cat > main.py << EOF
import time
print("Bot started successfully!")
while True:
    print("Bot is running...")
    time.sleep(5)
EOF

curl -s -X POST $API_URL/bots/$BOT_ID/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@main.py" | jq

# 4. Start bot
echo -e "\n4. Starting bot..."
curl -s -X POST $API_URL/bots/$BOT_ID/start \
  -H "Authorization: Bearer $TOKEN" | jq

# 5. Wait and check status
echo -e "\n5. Waiting 10 seconds..."
sleep 10

# 6. List bots
echo -e "\n6. Listing bots..."
curl -s $API_URL/bots \
  -H "Authorization: Bearer $TOKEN" | jq

# 7. Stop bot
echo -e "\n7. Stopping bot..."
curl -s -X POST $API_URL/bots/$BOT_ID/stop \
  -H "Authorization: Bearer $TOKEN" | jq

# 8. Delete bot
echo -e "\n8. Deleting bot..."
curl -s -X DELETE $API_URL/bots/$BOT_ID \
  -H "Authorization: Bearer $TOKEN"

# Cleanup
rm -f main.py

echo -e "\n✓ Workflow complete!"
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid bot name. Use 3-50 alphanumeric characters, hyphens, or underscores."
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "detail": "You don't have access to this bot"
}
```

### 404 Not Found
```json
{
  "detail": "Bot not found"
}
```

### 409 Conflict
```json
{
  "detail": "A bot with this name already exists"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Too many requests. Please try again later."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Tips

1. **Save Your Token**: Store the JWT token in an environment variable:
   ```bash
   export TOKEN="your_token_here"
   curl -H "Authorization: Bearer $TOKEN" ...
   ```

2. **Use jq for Pretty JSON**: Install `jq` and pipe responses through it:
   ```bash
   curl ... | jq
   ```

3. **Rate Limiting**: If you hit rate limits, wait a minute before retrying.

4. **Security**: Never commit tokens or credentials to version control.

5. **Testing**: Use the interactive API docs at `http://localhost:8000/docs` for easier testing.
