/**
 * Node.js bot with external dependencies example.
 * This bot uses axios to make HTTP calls.
 */

const axios = require('axios');

const formatTime = () => {
    const now = new Date();
    return now.toTimeString().split(' ')[0];
};

const fetchQuote = async () => {
    try {
        const response = await axios.get('https://api.quotable.io/random', {
            timeout: 5000
        });
        const data = response.data;
        return `"${data.content}" - ${data.author}`;
    } catch (error) {
        return `Failed to fetch quote: ${error.message}`;
    }
};

const main = async () => {
    console.log("=".repeat(50));
    console.log("Node.js Bot with Dependencies");
    console.log("=".repeat(50));
    console.log(`Started at: ${new Date().toISOString()}`);
    console.log();

    let iteration = 0;
    let running = true;

    const runLoop = async () => {
        while (running) {
            iteration++;
            console.log(`\n[Iteration ${iteration}] ${formatTime()}`);

            // Fetch and display a quote
            const quote = await fetchQuote();
            console.log(`Quote of the moment: ${quote}`);

            // Wait before next iteration
            console.log("Waiting 30 seconds...");
            await new Promise(resolve => setTimeout(resolve, 30000));
        }
    };

    // Handle graceful shutdown
    const shutdown = () => {
        running = false;
        console.log("\n" + "=".repeat(50));
        console.log("Bot stopped");
        console.log(`Completed ${iteration} iterations`);
        console.log("=".repeat(50));
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
