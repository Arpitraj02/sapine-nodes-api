# Bot Examples

This directory contains example bots for the Sapine Bot Hosting Platform.

## Available Examples

### Python Bots

Located in `python/` directory:

1. **simple_bot.py** - Basic bot that prints messages every 5 seconds
2. **bot_with_dependencies.py** - Bot that uses the `requests` library

See [python/README.md](python/README.md) for detailed usage instructions.

### Node.js Bots

Located in `nodejs/` directory:

1. **simple_bot.js** - Basic bot that prints messages every 5 seconds
2. **bot_with_dependencies.js** - Bot that uses the `axios` library

See [nodejs/README.md](nodejs/README.md) for detailed usage instructions.

## Quick Start

### 1. Register and Login

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123"
  }'

# Save the token
export TOKEN="your_access_token_here"
```

### 2. Create a Bot

```bash
# For Python
curl -X POST http://localhost:8000/bots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-python-bot",
    "runtime": "python",
    "start_cmd": "python simple_bot.py",
    "plan_id": 1
  }'

# For Node.js
curl -X POST http://localhost:8000/bots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-nodejs-bot",
    "runtime": "node",
    "start_cmd": "node simple_bot.js",
    "plan_id": 1
  }'
```

Save the bot ID from the response.

### 3. Upload Bot Code

```bash
# For single file
curl -X POST http://localhost:8000/bots/BOT_ID/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@examples/python/simple_bot.py"

# For zip archive with dependencies
cd examples/python
zip bot.zip bot_with_dependencies.py requirements.txt
cd ../..

curl -X POST http://localhost:8000/bots/BOT_ID/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@examples/python/bot.zip"
```

### 4. Start the Bot

```bash
curl -X POST http://localhost:8000/bots/BOT_ID/start \
  -H "Authorization: Bearer $TOKEN"
```

### 5. View Logs

Connect to WebSocket to see real-time logs:

```javascript
const ws = new WebSocket(`ws://localhost:8000/bots/${botId}/logs?token=${token}`);
ws.onmessage = (event) => console.log(event.data);
```

Or use a WebSocket client like `wscat`:

```bash
wscat -c "ws://localhost:8000/bots/BOT_ID/logs?token=$TOKEN"
```

## Testing Script

Here's a complete testing script:

```bash
#!/bin/bash
set -e

API_URL="http://localhost:8000"

echo "1. Registering user..."
RESPONSE=$(curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123"
  }')

TOKEN=$(echo $RESPONSE | jq -r '.access_token')
echo "Token: $TOKEN"

echo -e "\n2. Creating Python bot..."
BOT_RESPONSE=$(curl -s -X POST $API_URL/bots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-bot",
    "runtime": "python",
    "start_cmd": "python simple_bot.py",
    "plan_id": 1
  }')

BOT_ID=$(echo $BOT_RESPONSE | jq -r '.id')
echo "Bot ID: $BOT_ID"

echo -e "\n3. Uploading bot code..."
curl -s -X POST $API_URL/bots/$BOT_ID/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@examples/python/simple_bot.py" | jq

echo -e "\n4. Starting bot..."
curl -s -X POST $API_URL/bots/$BOT_ID/start \
  -H "Authorization: Bearer $TOKEN" | jq

echo -e "\n5. Waiting 15 seconds..."
sleep 15

echo -e "\n6. Stopping bot..."
curl -s -X POST $API_URL/bots/$BOT_ID/stop \
  -H "Authorization: Bearer $TOKEN" | jq

echo -e "\n✓ Test complete!"
```

## Creating Your Own Bot

### Guidelines

1. **Choose a runtime**: Python or Node.js
2. **Create your bot code**: Main file + optional dependencies
3. **Test locally first**: Make sure it runs on your machine
4. **Keep it simple**: Start with basic functionality
5. **Add logging**: Use print/console.log for debugging
6. **Handle signals**: Graceful shutdown on SIGTERM/SIGINT

### File Structure

For Python:
```
my-bot/
├── main.py              # Your bot code
└── requirements.txt     # Dependencies (optional)
```

For Node.js:
```
my-bot/
├── index.js            # Your bot code
└── package.json        # Dependencies (optional)
```

### Best Practices

1. **Logging**
   - Use print() or console.log()
   - Include timestamps
   - Log important events

2. **Error Handling**
   - Use try/catch or try/except
   - Log errors clearly
   - Don't crash on recoverable errors

3. **Resource Management**
   - Use sleep/setTimeout to avoid CPU overuse
   - Close connections properly
   - Don't write large files

4. **Security**
   - Don't expose API keys in logs
   - Validate input data
   - Use environment variables for secrets

5. **Dependencies**
   - Keep them minimal
   - Use stable versions
   - List all dependencies

## Supported Runtimes

### Python 3.11

- **Image**: python:3.11-slim
- **Package Manager**: pip
- **Dependency File**: requirements.txt
- **Allowed Extensions**: .py, .txt, .json, .yaml, .yml
- **Example Command**: `python main.py`

### Node.js 20

- **Image**: node:20-alpine
- **Package Manager**: npm
- **Dependency File**: package.json
- **Allowed Extensions**: .js, .json, .ts
- **Example Command**: `node index.js`

## Troubleshooting

### Bot won't start

- Check that you uploaded files
- Verify start command matches your filename
- Check logs for error messages

### Build fails

- Verify dependencies are correct
- Check requirements.txt or package.json syntax
- Ensure dependency versions are compatible

### Bot stops immediately

- Check for syntax errors in your code
- Verify your bot has a loop to keep running
- Check for unhandled exceptions

### Logs not showing

- Ensure bot is running
- Check WebSocket connection
- Verify authentication token is valid

## Support

For more information:
- API Documentation: http://localhost:8000/docs
- API Testing Guide: [API_TESTING.md](../API_TESTING.md)
- Security Guide: [SECURITY.md](../SECURITY.md)
