
from typing import List
import requests
from nio import AsyncClient
import asyncio

async def get_all_rooms(base_url = None, access_token = None, limit=10) -> List[dict]:
    """
    Fetches all rooms (groups) from the Synapse server using the admin API.

    Args:
    - base_url (str): The base URL of your Synapse server (e.g., https://your-synapse-server).
    - access_token (str): The access token for authenticating the request.
    - limit (int): Number of rooms to fetch per request (default is 10).

    Returns:
    - List of all rooms retrieved from the API.
    """

    # admin_client = AsyncClient(base_url, "@admin:messenger.b1.shuwantech.com")
    # await admin_client.login("thisismy.password")
    # access_token = admin_client.access_token
    access_token = "syt_YWRtaW4_gMTsSJZBrdvPETTwsBlW_21Id5N"
    # base_url = "https://messenger.b1.shuwantech.com"
    print(access_token)

    # Define the base API endpoint
    url = f"{base_url}/_synapse/admin/v1/rooms"

    
    # Set up headers with the access token
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Initialize variables for pagination
    all_rooms = []
    params = {
        "from": 0,   # Start from the beginning
        "limit": limit, # Fetch 'limit' rooms at a time
    }

    # Loop to paginate through all rooms
    while True:
        # Send the GET request
        response = requests.get(url, headers=headers, params=params)
        
        # Check if the request was successful
        if response.status_code >= 200 and response.status_code < 300:
            # Parse the response data
            rooms_data = response.json()
            rooms = rooms_data.get('rooms', [])
            
            # If no rooms are returned, break the loop
            if not rooms:
                break
            
            # Add the current batch of rooms to the list
            all_rooms.extend(rooms)
            
            # Update the 'from' parameter to get the next batch of rooms
            params['from'] += limit
        else:
            print(f"Failed to retrieve rooms: {response.status_code} - {response.text}")
            break

    print(all_rooms)
    return all_rooms

asyncio.run(get_all_rooms(base_url="https://messenger.b1.shuwantech.com"))
