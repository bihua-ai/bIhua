import asyncio
import importlib.util
import importlib
import os
from nio import AsyncClient, MatrixRoom, RoomMessageText

# Configuration
MATRIX_HOMESERVER = "https://messenger.b1.shuwantech.com"
USERNAME = "@bot_001:messenger.b1.shuwantech.com"
PASSWORD = "thisismy.password"

# Path to the agent script
agent_script_path = "/opt/bihua_cient/agents/bot_001.py"

def extract_handler_name(script_path):
    """Extract handler name from the agent script path."""
    # Extract the filename without extension (e.g., 'bot_001' from '/opt/bihua_cient/agents/bot_001.py')
    filename = os.path.basename(script_path)
    handler_name, _ = os.path.splitext(filename)
    return handler_name

def import_handler(handler_name):
    """Dynamically import the handler for the agent."""
    try:
        # Construct the import path (e.g., 'agents.bot_001')
        module_path = f"agents.{handler_name}"
        module = importlib.import_module(module_path)
        handler = getattr(module, f"on_message_received_{handler_name}")
        return handler
    except (ModuleNotFoundError, AttributeError) as e:
        print(f"Error loading handler: {e}")
        return None

async def message_callback(room: MatrixRoom, event: RoomMessageText):
    """Callback function to handle messages."""
    # Extract the handler name from the agent script path
    handler_name = extract_handler_name(agent_script_path)

    # Dynamically import the handler based on the script path
    handler = import_handler(handler_name)

    if handler is None:
        print("Handler not found or failed to load.")
        return

    # Wrap the event for compatibility with the dynamically loaded handler
    class EventWrapper:
        def __init__(self, body, room_id, event_type):
            self.body = body
            self.room_id = room_id
            self.type = event_type

    event_wrapper = EventWrapper(event.body, room.room_id, "m.room.message")
    await handler(event_wrapper, client)  # Call the dynamically loaded handler

async def main():
    """Main function to log in and start listening for messages."""
    global client
    client = AsyncClient(MATRIX_HOMESERVER, USERNAME)
    response = await client.login(PASSWORD)

    # Register message callback
    client.add_event_callback(message_callback, RoomMessageText)

    # Sync with the server
    try:
        print("Starting sync loop...")
        await client.sync_forever(timeout=30000)  # Sync every 30 seconds
    except Exception as e:
        print(f"Error during sync: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
