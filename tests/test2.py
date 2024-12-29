from nio import AsyncClient, LoginResponse
import asyncio

# Replace these with your server details
MATRIX_HOMESERVER = "https://messenger.b1.shuwantech.com"  # Example homeserver URL
USERNAME = "@bot_001:messenger.b1.shuwantech.com"
PASSWORD = "thisismy.password"

async def get_room_ids():
    # Create an async client for interacting with the Matrix server
    client = AsyncClient(MATRIX_HOMESERVER, USERNAME)
    
    try:
        # Log in to the server
        response = await client.login(PASSWORD)
        print(client.access_token)
        
        if isinstance(response, LoginResponse):
            print("Login successful!")
        else:
            print(f"Failed to log in: {response}")
            return
        
        # Fetch the list of joined rooms
        rooms = await client.joined_rooms()
        
        if hasattr(rooms, "rooms"):
            print("Joined room IDs:")
            for room_id in rooms.rooms:
                print(room_id)
        else:
            print("Could not fetch room IDs.")
    
    finally:
        # Close the client
        await client.close()

# Run the async function
asyncio.run(get_room_ids())
