# agent_002.py
from nio import AsyncClient, AsyncClientConfig, MatrixRoom, RoomMessageText

async def on_message_received_bot_002(event, client):
    """Custom handler for agent 1."""
    print(f"agent_002 processing message: {event.body}")
    # if event.type == "m.room.message":
    #     response = f"Hello from agent_002! You said: {event.body}"
    #     await client.send_message(event.room_id, response)
