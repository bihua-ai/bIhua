import asyncio
import importlib.util
import importlib
from nio import AsyncClient, MatrixRoom, RoomMessageText

# Configuration
MATRIX_HOMESERVER = "https://messenger.b1.shuwantech.com"
USERNAME = "@bot_001:messenger.b1.shuwantech.com"
PASSWORD = "thisismy.password"

# Path to the agent script
agent_script_path = "/opt/bihua_cient/agents/bot_001.py"

def import_handler(self, on_message_received):
        """Dynamically import the handler for the agent."""
        try:

            module = importlib.import_module(f"agents.{on_message_received}")
            handler = getattr(module, f"on_message_received_{on_message_received}")

            return handler
        except (ModuleNotFoundError, AttributeError) as e:
            return None

def load_callback(script_path: str):
    """Dynamically load the callback function from the agent script."""
    spec = importlib.util.spec_from_file_location("bot_001", script_path)
    print(spec)
    agent_module = importlib.util.module_from_spec(spec)
    print(agent_module)
    spec.loader.exec_module(agent_module)
    print("in load_callback")
    print(agent_module)
    print(agent_module.on_message_received_bot_001)
    return agent_module.on_message_received_bot_001

# Dynamically load the callback function
hander_mine = load_callback(agent_script_path)

async def message_callback(room: MatrixRoom, event: RoomMessageText):
    """Callback function to handle messages."""
    # Wrap the dynamically loaded callback for compatibility
    class EventWrapper:
        def __init__(self, body, room_id, event_type):
            self.body = body
            self.room_id = room_id
            self.type = event_type

    event_wrapper = EventWrapper(event.body, room.room_id, "m.room.message")
    await hander_mine(event_wrapper, client)


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
