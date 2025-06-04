import asyncio
import websockets
import json
import logging
import sys
import os # For environment variables

# Configure logging for better visibility of agent actions
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Agent Configuration ---
# Use environment variables for server URI and authentication token
SERVER_URI = os.getenv("SERVER_URI", "ws://localhost:8765")
AUTH_TOKEN = os.getenv("AGENT_AUTH_SECRET", "super_secret_key_123") # Must match server's SHARED_SECRET

class Agent:
    """
    Represents an individual agent capable of connecting to the communication server,
    sending messages to other agents, and receiving messages.
    This version focuses on CLI-based interactive chat with enhanced server features.
    """
    def __init__(self, agent_id, server_uri=SERVER_URI, auth_token=AUTH_TOKEN):
        self.agent_id = agent_id
        self.server_uri = server_uri
        self.auth_token = auth_token
        self.websocket = None
        self.is_connected = False
        self.online_agents = [] # To store the list of online agents
        logging.info(f"Agent '{self.agent_id}' initialized. Connecting to {self.server_uri}.")

    async def connect(self):
        """
        Establishes a WebSocket connection to the server and registers the agent with authentication.
        Returns True on successful connection and registration, False otherwise.
        """
        try:
            logging.info(f"Agent '{self.agent_id}' attempting to connect to {self.server_uri}...")
            self.websocket = await websockets.connect(self.server_uri)
            self.is_connected = True
            logging.info(f"Agent '{self.agent_id}' connected to server.")

            # Send the registration message with authentication token
            registration_message = {
                "type": "AGENT_REGISTER",
                "agent_id": self.agent_id,
                "auth_token": self.auth_token
            }
            await self.websocket.send(json.dumps(registration_message))
            logging.info(f"Agent '{self.agent_id}' sent registration message with token.")

            # Wait for the server's initial response (welcome or error)
            initial_response_str = await self.websocket.recv()
            initial_response = json.loads(initial_response_str)

            if initial_response.get("type") == "SERVER_INFO":
                logging.info(f"Server response: {initial_response.get('content')}")
                return True
            elif initial_response.get("type") == "SERVER_ERROR":
                logging.error(f"Server rejected connection for '{self.agent_id}': {initial_response.get('content')}")
                await self.websocket.close()
                self.is_connected = False
                return False
            else:
                logging.warning(f"Unexpected initial server response from '{self.server_uri}': {initial_response_str}")
                await self.websocket.close()
                self.is_connected = False
                return False

        except websockets.exceptions.ConnectionRefusedError:
            logging.error(f"Agent '{self.agent_id}' failed to connect: Connection refused. Is the server running?")
            self.is_connected = False
            return False
        except Exception as e:
            logging.error(f"Agent '{self.agent_id}' failed to connect to server: {e}", exc_info=True)
            self.is_connected = False
            return False

    async def send_message(self, receiver_id, content):
        """Sends a direct message to a specific agent."""
        if not self.is_connected or not self.websocket or self.websocket.closed:
            logging.error(f"Agent '{self.agent_id}' not connected. Cannot send message to '{receiver_id}'.")
            return

        message = {
            "type": "AGENT_MESSAGE",
            "sender_id": self.agent_id,
            "receiver_id": receiver_id,
            "content": content
        }
        try:
            await self.websocket.send(json.dumps(message))
            logging.info(f"Agent '{self.agent_id}' sent message to '{receiver_id}'.")
        except Exception as e:
            logging.error(f"Agent '{self.agent_id}' failed to send message to '{receiver_id}': {e}", exc_info=True)
            self.is_connected = False

    async def broadcast_message(self, content):
        """Sends a message to all connected agents."""
        if not self.is_connected or not self.websocket or self.websocket.closed:
            logging.error(f"Agent '{self.agent_id}' not connected. Cannot broadcast message.")
            return

        message = {
            "type": "BROADCAST_MESSAGE",
            "sender_id": self.agent_id,
            "content": content
        }
        try:
            await self.websocket.send(json.dumps(message))
            logging.info(f"Agent '{self.agent_id}' sent broadcast message.")
        except Exception as e:
            logging.error(f"Agent '{self.agent_id}' failed to broadcast message: {e}", exc_info=True)
            self.is_connected = False

    async def request_online_agents(self):
        """Requests a list of currently online agents from the server."""
        if not self.is_connected or not self.websocket or self.websocket.closed:
            logging.error(f"Agent '{self.agent_id}' not connected. Cannot request online agents.")
            return

        message = {
            "type": "LIST_AGENTS_REQUEST",
            "sender_id": self.agent_id
        }
        try:
            await self.websocket.send(json.dumps(message))
            logging.info(f"Agent '{self.agent_id}' requested online agents list.")
        except Exception as e:
            logging.error(f"Agent '{self.agent_id}' failed to request online agents: {e}", exc_info=True)
            self.is_connected = False

    async def _receive_messages_task(self):
        """
        Asynchronously listens for incoming messages from the server and prints them.
        Handles different message types including direct messages, broadcasts, and server responses.
        """
        try:
            async for message_str in self.websocket:
                try:
                    message = json.loads(message_str)
                    message_type = message.get("type")

                    if message_type == "AGENT_MESSAGE":
                        sender_id = message.get("sender_id")
                        content = message.get("content")
                        print(f"\n[DM from {sender_id}]: {content}\n> ", end="", flush=True)
                    elif message_type == "BROADCAST_MESSAGE":
                        sender_id = message.get("sender_id")
                        content = message.get("content")
                        print(f"\n[BROADCAST from {sender_id}]: {content}\n> ", end="", flush=True)
                    elif message_type == "LIST_AGENTS_RESPONSE":
                        agents = message.get("agents", [])
                        self.online_agents = agents # Update local list
                        print(f"\n[SERVER INFO]: Online Agents: {', '.join(agents) if agents else 'None'}\n> ", end="", flush=True)
                    elif message_type == "SERVER_ERROR":
                        print(f"\n[SERVER ERROR]: {message.get('content')}\n> ", end="", flush=True)
                    elif message_type == "SERVER_INFO":
                        print(f"\n[SERVER INFO]: {message.get('content')}\n> ", end="", flush=True)
                    else:
                        logging.warning(f"Agent '{self.agent_id}' received unknown message type: {message_type}. Message: {message_str}")
                except json.JSONDecodeError:
                    logging.error(f"Agent '{self.agent_id}' received invalid JSON: {message_str}")
                except Exception as e:
                    logging.error(f"Agent '{self.agent_id}' error processing received message: {e}", exc_info=True)
        except websockets.exceptions.ConnectionClosedOK:
            logging.info(f"Agent '{self.agent_id}' connection to server closed normally.")
        except websockets.exceptions.ConnectionClosedError as e:
            logging.error(f"Agent '{self.agent_id}' connection to server closed with error: {e}")
        except Exception as e:
            logging.critical(f"Agent '{self.agent_id}' unexpected error in receive loop: {e}", exc_info=True)
        finally:
            self.is_connected = False
            logging.info(f"Agent '{self.agent_id}' message reception stopped.")

    async def _send_cli_messages_task(self):
        """
        Asynchronously reads messages from standard input and sends them.
        Supports commands for direct messages, broadcasts, and listing agents.
        """
        print(f"You are '{self.agent_id}'. Commands: /list, /broadcast <message>, /msg <target_id> <message>, exit")
        while self.is_connected:
            try:
                user_input = await asyncio.to_thread(input, "> ")
                if user_input.lower() == 'exit':
                    break
                elif user_input.lower() == '/list':
                    await self.request_online_agents()
                elif user_input.lower().startswith('/broadcast '):
                    content = user_input[len('/broadcast '):].strip()
                    if content:
                        await self.broadcast_message(content)
                    else:
                        print("Usage: /broadcast <message>")
                elif user_input.lower().startswith('/msg '):
                    parts = user_input.split(' ', 2) # Split into /msg, target_id, message
                    if len(parts) == 3:
                        target_id = parts[1]
                        content = parts[2].strip()
                        if target_id and content:
                            await self.send_message(target_id, content)
                        else:
                            print("Usage: /msg <target_id> <message>")
                    else:
                        print("Usage: /msg <target_id> <message>")
                elif user_input:
                    # If no command, prompt user to use /msg or /broadcast
                    print("Unknown command. Use /msg <target_id> <message> or /broadcast <message> or /list.")
            except EOFError:
                logging.info("EOF received, exiting CLI input task.")
                break
            except Exception as e:
                logging.error(f"Error reading CLI input for '{self.agent_id}': {e}", exc_info=True)
                break
        logging.info(f"Agent '{self.agent_id}' CLI input task stopped.")


async def main():
    """
    Main function to run an agent for interactive CLI chat.
    Requires agent_id as a command-line argument.
    """
    if len(sys.argv) < 2:
        print("Usage: python agent.py <your_agent_id>")
        sys.exit(1)

    agent_id = sys.argv[1]
    agent = Agent(agent_id)

    if not await agent.connect():
        logging.error(f"Agent '{agent_id}' could not connect. Exiting.")
        return

    receive_task = asyncio.create_task(agent._receive_messages_task())
    send_task = asyncio.create_task(agent._send_cli_messages_task())

    await asyncio.gather(receive_task, send_task)

    logging.info(f"Agent '{agent_id}' shutting down.")
    if agent.websocket and not agent.websocket.closed:
        await agent.websocket.close()
        logging.info(f"Agent '{agent_id}' WebSocket connection closed.")

if __name__ == "__main__":
    asyncio.run(main())
