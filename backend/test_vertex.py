
import asyncio
import structlog
import sys
import os

# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.vertex_client import get_vertex_client

# Configure basic logging to stdout
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

async def test_vertex():
    print("Testing Vertex AI Connection with multiple models...")
    client = get_vertex_client()
    
    messages = [
        {"role": "user", "content": "Hello, simply reply with 'OK'."}
    ]
    
    # List of models to try
    models_to_test = [
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro-002",
        "gemini-1.5-flash-002"
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
    asyncio.run(test_vertex())
