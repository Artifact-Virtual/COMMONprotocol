import asyncio
import websockets
import json
import logging
import os # For environment variables

# Configure logging for better visibility of server actions
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Server Configuration ---
# Use environment variables for host and port, with sensible defaults
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 8765))

# A simple shared secret for agent authentication.
# In a real-world scenario, this would be much more sophisticated (e.g., JWTs, OAuth).
SHARED_SECRET = os.getenv("AGENT_AUTH_SECRET", "super_secret_key_123")
if SHARED_SECRET == "super_secret_key_123":
    logging.warning("Using default SHARED_SECRET. PLEASE CHANGE THIS IN PRODUCTION!")

# Dictionary to store active agent connections.
# Key: agent_id (string), Value: websocket connection object
CONNECTED_AGENTS = {}

async def register_agent(websocket, agent_id):
    """
    Registers a new agent connection.
    Adds the agent's websocket to the CONNECTED_AGENTS dictionary.
    Sends a confirmation message back to the newly connected agent.
    """
    CONNECTED_AGENTS[agent_id] = websocket
    logging.info(f"Agent '{agent_id}' connected and registered. Total active agents: {len(CONNECTED_AGENTS)}")
    await websocket.send(json.dumps({"type": "SERVER_INFO", "content": f"Welcome, agent {agent_id}! You are now online."}))

async def unregister_agent(agent_id):
    """
    Unregisters an agent.
    Removes the agent's entry from the CONNECTED_AGENTS dictionary.
    """
    if agent_id in CONNECTED_AGENTS:
        del CONNECTED_AGENTS[agent_id]
        logging.info(f"Agent '{agent_id}' disconnected and unregistered. Remaining active agents: {len(CONNECTED_AGENTS)}")

async def handle_agent_connection(websocket, path):
    """
    Main handler for each new WebSocket connection.
    It manages the authentication, registration, and then continuously listens for messages
    from the connected agent, routing them to the intended recipient or handling server commands.
    """
    agent_id = None # Initialize agent_id to None
    try:
        # --- Step 1: Agent Authentication and Registration ---
        logging.info("Waiting for agent authentication and registration message...")
        auth_reg_message_str = await websocket.recv()
        auth_reg_message = json.loads(auth_reg_message_str)

        if auth_reg_message.get("type") == "AGENT_REGISTER":
            agent_id = auth_reg_message.get("agent_id")
            auth_token = auth_reg_message.get("auth_token")

            if not agent_id:
                logging.warning("Received registration message without 'agent_id'. Closing connection.")
                await websocket.send(json.dumps({"type": "SERVER_ERROR", "content": "Registration failed: 'agent_id' is missing."}))
                return
            if auth_token != SHARED_SECRET:
                logging.warning(f"Agent '{agent_id}' provided invalid auth_token. Closing connection.")
                await websocket.send(json.dumps({"type": "SERVER_ERROR", "content": "Authentication failed: Invalid token."}))
                return
            if agent_id in CONNECTED_AGENTS:
                logging.warning(f"Agent '{agent_id}' attempted to connect, but an agent with this ID is already online. Closing new connection.")
                await websocket.send(json.dumps({"type": "SERVER_ERROR", "content": f"Agent ID '{agent_id}' is already in use. Please choose a different ID."}))
                return

            await register_agent(websocket, agent_id)
        else:
            logging.warning(f"First message was not an 'AGENT_REGISTER' type. Received: {auth_reg_message_str}. Closing connection.")
            await websocket.send(json.dumps({"type": "SERVER_ERROR", "content": "Initial message must be an 'AGENT_REGISTER' type with auth_token."}))
            return

        # --- Step 2: Message Routing and Command Handling Loop ---
        async for message_str in websocket:
            try:
                message = json.loads(message_str)
                message_type = message.get("type")
                sender_id = message.get("sender_id") # Assuming sender_id is always present after registration

                if message_type == "AGENT_MESSAGE":
                    receiver_id = message.get("receiver_id")
                    content = message.get("content")

                    if not all([sender_id, receiver_id, content]):
                        logging.warning(f"Incomplete AGENT_MESSAGE from '{sender_id}'. Message: {message_str}")
                        await websocket.send(json.dumps({
                            "type": "SERVER_ERROR",
                            "content": "Message missing sender_id, receiver_id, or content."
                        }))
                        continue

                    logging.info(f"Received message from '{sender_id}' for '{receiver_id}': '{content}'")

                    if receiver_id in CONNECTED_AGENTS:
                        receiver_websocket = CONNECTED_AGENTS[receiver_id]
                        await receiver_websocket.send(message_str)
                        logging.info(f"Successfully routed message from '{sender_id}' to '{receiver_id}'.")
                    else:
                        logging.warning(f"Receiver '{receiver_id}' not found or offline. Message from '{sender_id}' dropped.")
                        await websocket.send(json.dumps({
                            "type": "SERVER_ERROR",
                            "content": f"Agent '{receiver_id}' is not online. Message not delivered."
                        }))

                elif message_type == "BROADCAST_MESSAGE":
                    content = message.get("content")
                    if not all([sender_id, content]):
                        logging.warning(f"Incomplete BROADCAST_MESSAGE from '{sender_id}'. Message: {message_str}")
                        await websocket.send(json.dumps({
                            "type": "SERVER_ERROR",
                            "content": "Broadcast message missing sender_id or content."
                        }))
                        continue

                    logging.info(f"Received broadcast message from '{sender_id}': '{content}'")
                    # Send to all connected agents except the sender
                    for agent_id_online, ws_conn in CONNECTED_AGENTS.items():
                        if agent_id_online != sender_id:
                            try:
                                await ws_conn.send(message_str)
                                logging.debug(f"Broadcasted from '{sender_id}' to '{agent_id_online}'.")
                            except Exception as e:
                                logging.error(f"Error broadcasting message to '{agent_id_online}': {e}")
                    logging.info(f"Broadcast message from '{sender_id}' sent to all other online agents.")

                elif message_type == "LIST_AGENTS_REQUEST":
                    logging.info(f"Received LIST_AGENTS_REQUEST from '{sender_id}'.")
                    online_agents = list(CONNECTED_AGENTS.keys())
                    await websocket.send(json.dumps({
                        "type": "LIST_AGENTS_RESPONSE",
                        "agents": online_agents,
                        "requester_id": sender_id
                    }))
                    logging.info(f"Sent LIST_AGENTS_RESPONSE to '{sender_id}'. Online agents: {online_agents}")

                else:
                    logging.warning(f"Unknown message type received from '{agent_id}': {message_type}. Message: {message_str}")
                    await websocket.send(json.dumps({
                        "type": "SERVER_ERROR",
                        "content": f"Unknown message type '{message_type}'."
                    }))

            except json.JSONDecodeError:
                logging.error(f"Invalid JSON received from '{agent_id}': {message_str}")
                await websocket.send(json.dumps({
                    "type": "SERVER_ERROR",
                    "content": "Invalid JSON format received."
                }))
            except Exception as e:
                logging.error(f"Error processing message from '{agent_id}': {e}", exc_info=True)
                await websocket.send(json.dumps({
                    "type": "SERVER_ERROR",
                    "content": f"Internal server error while processing your message."
                }))

    except websockets.exceptions.ConnectionClosedOK:
        logging.info(f"Agent '{agent_id if agent_id else 'unknown'}' connection closed normally.")
    except websockets.exceptions.ConnectionClosedError as e:
        logging.error(f"Agent '{agent_id if agent_id else 'unknown'}' connection closed with error: {e}")
    except Exception as e:
        logging.critical(f"Unexpected error in handle_agent_connection for '{agent_id if agent_id else 'unregistered'}' connection: {e}", exc_info=True)
    finally:
        if agent_id:
            await unregister_agent(agent_id)

async def main():
    """
    Starts the WebSocket server.
    """
    logging.info(f"Starting WebSocket server on ws://{SERVER_HOST}:{SERVER_PORT}")
    async with websockets.serve(handle_agent_connection, SERVER_HOST, SERVER_PORT):
        await asyncio.Future() # Keep the server running indefinitely

if __name__ == "__main__":
    asyncio.run(main())
