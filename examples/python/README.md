# Python Bot Examples

This directory contains example Python bots you can use with the Sapine Bot Hosting Platform.

## Simple Bot

**File:** `simple_bot.py`

A basic bot that prints messages every 5 seconds. Perfect for testing the platform.

### Usage:

1. Create a bot:
```bash
curl -X POST http://localhost:8000/bots \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "simple-python-bot",
    "runtime": "python",
    "start_cmd": "python simple_bot.py",
    "plan_id": 1
  }'
```

2. Upload the file:
```bash
curl -X POST http://localhost:8000/bots/{bot_id}/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@examples/python/simple_bot.py"
```

3. Start the bot:
```bash
curl -X POST http://localhost:8000/bots/{bot_id}/start \
  -H "Authorization: Bearer YOUR_TOKEN"
```

4. View logs via WebSocket to see the output.

## Bot with Dependencies

**Files:** `bot_with_dependencies.py`, `requirements.txt`

A bot that uses the `requests` library to fetch random quotes from an API.

### Usage:

1. Create a bot:
```bash
curl -X POST http://localhost:8000/bots \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "python-bot-deps",
    "runtime": "python",
    "start_cmd": "python bot_with_dependencies.py",
    "plan_id": 1
  }'
```

2. Create a zip file:
```bash
cd examples/python
zip bot.zip bot_with_dependencies.py requirements.txt
```

3. Upload the zip:
```bash
curl -X POST http://localhost:8000/bots/{bot_id}/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@examples/python/bot.zip"
```

4. Start the bot:
```bash
curl -X POST http://localhost:8000/bots/{bot_id}/start \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Creating Your Own Bot

When creating your own Python bot:

1. **Main file**: Create a Python file (e.g., `main.py`, `bot.py`)
2. **Dependencies**: If you need external packages, create a `requirements.txt`
3. **Start command**: Use `python your_file.py` as the start command
4. **Logging**: Use `print()` for logs (they'll appear in the console)
5. **Long-running**: Use a loop with `time.sleep()` to keep the bot running

### Best Practices:

- Add error handling with try/except
- Use `time.sleep()` to prevent CPU overuse
- Print informative log messages
- Handle graceful shutdown (KeyboardInterrupt)
- Keep dependencies minimal
- Avoid writing files (containers are ephemeral)

### Example Structure:

```python
import time
from datetime import datetime

def main():
    print("Bot starting...")
    
    try:
        while True:
            # Your bot logic here
            print(f"[{datetime.now()}] Bot is running")
            time.sleep(10)
    
    except KeyboardInterrupt:
        print("Bot stopped")

if __name__ == "__main__":
    main()
```
