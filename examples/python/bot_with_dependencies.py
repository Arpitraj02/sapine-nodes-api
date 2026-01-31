"""
Python bot with external dependencies example.
This bot uses the requests library to make HTTP calls.
"""

import time
import requests
from datetime import datetime

def fetch_quote():
    """Fetch a random quote from an API"""
    try:
        response = requests.get("https://api.quotable.io/random", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return f'"{data["content"]}" - {data["author"]}'
    except Exception as e:
        return f"Failed to fetch quote: {str(e)}"

def main():
    print("=" * 50)
    print("Python Bot with Dependencies")
    print("=" * 50)
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            print(f"\n[Iteration {iteration}] {datetime.now().strftime('%H:%M:%S')}")
            
            # Fetch and display a quote
            quote = fetch_quote()
            print(f"Quote of the moment: {quote}")
            
            # Wait before next iteration
            print("Waiting 30 seconds...")
            time.sleep(30)
    
    except KeyboardInterrupt:
        print("\n" + "=" * 50)
        print("Bot stopped")
        print(f"Completed {iteration} iterations")
        print("=" * 50)

if __name__ == "__main__":
    main()
