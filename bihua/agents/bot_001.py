# agent_001.py
from nio import AsyncClient, AsyncClientConfig, MatrixRoom, RoomMessageText

async def on_message_received_bot_001(event, client):
    """Custom handler for agent 1."""
    print(f"agent_001 processing message AAA: {event.body}")
    # if event.type == "m.room.message":
    #     response = f"Hello from agent_001! You said: {event.body}"
    #     await client.send_message(event.room_id, response)
