# Node.js Bot Examples

This directory contains example Node.js bots you can use with the Sapine Bot Hosting Platform.

## Simple Bot

**File:** `simple_bot.js`

A basic bot that prints messages every 5 seconds. Perfect for testing the platform.

### Usage:

1. Create a bot:
```bash
curl -X POST http://localhost:8000/bots \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "simple-nodejs-bot",
    "runtime": "node",
    "start_cmd": "node simple_bot.js",
    "plan_id": 1
  }'
```

2. Upload the file:
```bash
curl -X POST http://localhost:8000/bots/{bot_id}/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@examples/nodejs/simple_bot.js"
```

3. Start the bot:
```bash
curl -X POST http://localhost:8000/bots/{bot_id}/start \
  -H "Authorization: Bearer YOUR_TOKEN"
```

4. View logs via WebSocket to see the output.

## Bot with Dependencies

**Files:** `bot_with_dependencies.js`, `package.json`

A bot that uses the `axios` library to fetch random quotes from an API.

### Usage:

1. Create a bot:
```bash
curl -X POST http://localhost:8000/bots \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nodejs-bot-deps",
    "runtime": "node",
    "start_cmd": "node bot_with_dependencies.js",
    "plan_id": 1
  }'
```

2. Create a zip file:
```bash
cd examples/nodejs
zip bot.zip bot_with_dependencies.js package.json
```

3. Upload the zip:
```bash
curl -X POST http://localhost:8000/bots/{bot_id}/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@examples/nodejs/bot.zip"
```

4. Start the bot:
```bash
curl -X POST http://localhost:8000/bots/{bot_id}/start \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Creating Your Own Bot

When creating your own Node.js bot:

1. **Main file**: Create a JavaScript file (e.g., `index.js`, `bot.js`)
2. **Dependencies**: If you need external packages, create a `package.json`
3. **Start command**: Use `node your_file.js` as the start command
4. **Logging**: Use `console.log()` for logs (they'll appear in the console)
5. **Long-running**: Use `setInterval()` or async loops to keep the bot running

### Best Practices:

- Add error handling with try/catch
- Use `setInterval()` or `setTimeout()` to prevent blocking
- Print informative log messages
- Handle graceful shutdown (SIGINT, SIGTERM)
- Keep dependencies minimal
- Avoid writing files (containers are ephemeral)
- Use async/await for cleaner asynchronous code

### Example Structure:

```javascript
const main = async () => {
    console.log("Bot starting...");
    
    let running = true;
    
    const runLoop = async () => {
        while (running) {
            // Your bot logic here
            console.log(`[${new Date().toISOString()}] Bot is running`);
            
            // Wait 10 seconds
            await new Promise(resolve => setTimeout(resolve, 10000));
        }
    };
    
    // Handle graceful shutdown
    const shutdown = () => {
        running = false;
        console.log("Bot stopped");
        process.exit(0);
    };
    
    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);
    
    await runLoop();
};

main().catch(error => {
    console.error("Fatal error:", error);
    process.exit(1);
});
```

### Package.json Template:

```json
{
  "name": "my-bot",
  "version": "1.0.0",
  "main": "index.js",
  "dependencies": {
    "axios": "^1.6.0"
  }
}
```

## Signal Handling

Node.js bots should handle signals for graceful shutdown:

- `SIGINT`: Ctrl+C / Interrupt
- `SIGTERM`: Termination signal from platform

Example:
```javascript
process.on('SIGINT', () => {
    console.log("Shutting down gracefully...");
    // Cleanup code here
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log("Termination signal received...");
    // Cleanup code here
    process.exit(0);
});
```
