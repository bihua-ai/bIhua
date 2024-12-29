import asyncio
import importlib.util
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

def load_callback(script_path: str):
    """Dynamically load the callback function from the agent script."""
    handler_name = extract_handler_name(script_path)
    
    spec = importlib.util.spec_from_file_location(handler_name, script_path)
    print(f"Module spec: {spec}")
    agent_module = importlib.util.module_from_spec(spec)
    print(f"Agent module: {agent_module}")
    spec.loader.exec_module(agent_module)

    # Construct the handler function name dynamically
    callback_function_name = f"on_message_received_{handler_name}"
    
    # Dynamically get the handler function from the module
    handler = getattr(agent_module, callback_function_name, None)
    if handler is None:
        print(f"Handler function '{callback_function_name}' not found in the module.")
    return handler

# Dynamically load the callback function
handler_mine = load_callback(agent_script_path)

async def message_callback(room: MatrixRoom, event: RoomMessageText):
    """Callback function to handle messages."""
    # Wrap the dynamically loaded callback for compatibility
    class EventWrapper:
        def __init__(self, body, room_id, event_type):
            self.body = body
            self.room_id = room_id
            self.type = event_type

    event_wrapper = EventWrapper(event.body, room.room_id, "m.room.message")
    
    if handler_mine:
        await handler_mine(event_wrapper, client)
    else:
        print("No handler found.")

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
