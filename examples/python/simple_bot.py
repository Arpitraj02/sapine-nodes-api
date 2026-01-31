"""
Simple Python bot example for Sapine Bot Hosting Platform.
This bot prints messages to demonstrate the logging system.
"""

import time
from datetime import datetime

def main():
    print("=" * 50)
    print("Simple Python Bot")
    print("=" * 50)
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    counter = 0
    try:
        while True:
            counter += 1
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Bot is running... (iteration {counter})")
            
            # Do some work
            time.sleep(5)
            
            # Log every 10 iterations
            if counter % 10 == 0:
                print(f"✓ Completed {counter} iterations")
    
    except KeyboardInterrupt:
        print("\n" + "=" * 50)
        print("Bot stopped by user")
        print(f"Total iterations: {counter}")
        print("=" * 50)

if __name__ == "__main__":
    main()
