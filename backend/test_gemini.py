
import asyncio
import structlog
import sys
import os

# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.gemini_client import get_gemini_client

# Configure basic logging to stdout
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

async def test_gemini():
    print("Testing Google AI Studio (Gemini) Connection with multiple models...")
    client = get_gemini_client()
    
    messages = [
        {"role": "user", "content": "Hello, simply reply with 'OK'."}
    ]
    
    # List of models to try
    models_to_test = [
        "gemini-3-flash-preview",
        "gemini-2.0-flash-exp",
    ]
    
    for model in models_to_test:
        print(f"\n--- Testing model: {model} ---")
        try:
            print(f"Calling endpoint for {model}...")
            # We bypass the default model and pass specific model
            response = await client.call_agent(
                model=model,
                messages=messages
            )
            print("Response received:")
            print(client.get_message_content(response))
            print(f"SUCCESS: {model} is working!")
            # If successful, we can stop or check others
        except Exception as e:
            print(f"FAILED: {model} - Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini())
