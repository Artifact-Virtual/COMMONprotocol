import asyncio
import aiohttp
import json
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Client Configuration ---
# Must match the relay server's configuration
RELAY_SERVER_URL = os.getenv("CLIENT_RELAY_URL", "http://localhost:8080/relay_llm_message")
RELAY_API_KEY = os.getenv("CLIENT_RELAY_API_KEY", "your_strong_secret_api_key_123") # Must match server's RELAY_API_KEY

# This is the URL of the *target* LLM that the relay server will forward the prompt to.
# If you're testing with local Ollama, this would be its API endpoint.
TARGET_LLM_URL = os.getenv("TARGET_LLM_URL", "http://localhost:11434/api/generate")
TARGET_LLM_MODEL = os.getenv("TARGET_LLM_MODEL", "llama3") # Model to request from target LLM

async def send_llm_prompt_via_relay(prompt: str, sender_id: str):
    """
    Sends an LLM prompt to the relay server, which then forwards it to the target LLM.
    """
    logging.info(f"'{sender_id}' sending prompt via relay: '{prompt[:50]}...'")

    payload = {
        "target_llm_url": TARGET_LLM_URL,
        "llm_prompt": prompt,
        "sender_id": sender_id,
        "llm_model": TARGET_LLM_MODEL
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": RELAY_API_KEY # Include the API key for authentication
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(RELAY_SERVER_URL, json=payload, headers=headers, timeout=300) as response:
                response_data = await response.json()
                if response.status == 200:
                    llm_response = response_data.get("llm_response", "No response text found.")
                    logging.info(f"'{sender_id}' received LLM response via relay: '{llm_response[:100]}...'")
                    print(f"\n--- LLM Response for '{sender_id}' ---\nPrompt: {prompt}\nResponse: {llm_response}\n----------------------------------\n")
                    return llm_response
                else:
                    error_message = response_data.get("error", "Unknown error from relay.")
                    logging.error(f"Error from relay server (status {response.status}): {error_message}")
                    print(f"\n--- Error from Relay ---\nStatus: {response.status}\nError: {error_message}\n----------------------\n")
                    return None
    except aiohttp.ClientConnectorError as e:
        logging.error(f"Failed to connect to relay server at {RELAY_SERVER_URL}: {e}. Is the relay server running?")
        print(f"\n--- Connection Error ---\nFailed to connect to relay server. Is it running at {RELAY_SERVER_URL}?\n------------------------\n")
        return None
    except asyncio.TimeoutError:
        logging.error(f"Request to relay server timed out after 300 seconds.")
        print(f"\n--- Timeout Error ---\nRequest to relay server timed out.\n---------------------\n")
        return None
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"\n--- Unexpected Error ---\nAn unexpected error occurred: {e}\n------------------------\n")
        return None

async def main():
    """
    Main function to run the LLM client example.
    """
    if len(sys.argv) < 2:
        print("Usage: python llm_client_example.py <your_llm_id>")
        sys.exit(1)

    my_llm_id = sys.argv[1]

    print(f"LLM Client '{my_llm_id}' started.")
    print(f"Targeting relay at: {RELAY_SERVER_URL}")
    print(f"Relay will forward to: {TARGET_LLM_URL} (model: {TARGET_LLM_MODEL})\n")

    # Example prompts
    prompts = [
        "Tell me a short story about a brave knight.",
        "Explain the concept of quantum entanglement in simple terms.",
        "Write a haiku about a sunset.",
        "What is the capital of Australia?"
    ]

    for i, prompt in enumerate(prompts):
        print(f"Sending prompt {i+1}/{len(prompts)}...")
        await send_llm_prompt_via_relay(prompt, my_llm_id)
        await asyncio.sleep(5) # Wait a bit before sending the next prompt

    print(f"\nLLM Client '{my_llm_id}' finished sending all example prompts.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("LLM Client stopped by user.")
    except Exception as e:
        logging.critical(f"An unhandled error occurred: {e}", exc_info=True)
