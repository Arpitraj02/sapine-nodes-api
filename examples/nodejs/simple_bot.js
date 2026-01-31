/**
 * Simple Node.js bot example for Sapine Bot Hosting Platform.
 * This bot prints messages to demonstrate the logging system.
 */

const formatTime = () => {
    const now = new Date();
    return now.toTimeString().split(' ')[0];
};

const main = async () => {
    console.log("=".repeat(50));
    console.log("Simple Node.js Bot");
    console.log("=".repeat(50));
    console.log(`Started at: ${new Date().toISOString()}`);
    console.log();

    let counter = 0;

    const interval = setInterval(() => {
        counter++;
        console.log(`[${formatTime()}] Bot is running... (iteration ${counter})`);

        // Log every 10 iterations
        if (counter % 10 === 0) {
            console.log(`✓ Completed ${counter} iterations`);
        }
    }, 5000);

    // Handle graceful shutdown
    process.on('SIGINT', () => {
        clearInterval(interval);
        console.log("\n" + "=".repeat(50));
        console.log("Bot stopped by user");
        console.log(`Total iterations: ${counter}`);
        console.log("=".repeat(50));
        process.exit(0);
    });

    process.on('SIGTERM', () => {
        clearInterval(interval);
        console.log("\n" + "=".repeat(50));
        console.log("Bot stopped");
        console.log(`Total iterations: ${counter}`);
        console.log("=".repeat(50));
        process.exit(0);
    });
};

main().catch(error => {
    console.error("Fatal error:", error);
    process.exit(1);
});
