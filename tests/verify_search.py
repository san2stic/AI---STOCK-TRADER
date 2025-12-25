import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from tools.trading_tools import TradingTools
from config import get_settings

async def test_search():
    print("Testing search_web tool...")
    tools = TradingTools("tester")
    
    # Test 1: Search with default settings (should use DDGS if no SERPAPI key or fall back)
    print("\n--- Test 1: Basic Search ---")
    result = await tools.search_web("Apple stock news", max_results=3)
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Success! Source used: {result.get('source', 'unknown')}")
        print(f"Found {result.get('count')} results")
        for r in result.get('results', []):
            print(f"- {r.get('title')} ({r.get('link')})")

if __name__ == "__main__":
    asyncio.run(test_search())
