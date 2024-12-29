from typing import List
import requests
from nio import AsyncClient
import asyncio, os
from bihua_logging import get_logger
import utilities
from status_definitions import CrudStatus
from dotenv import load_dotenv

# Logger setup
logger = get_logger()

# # GET /_synapse/admin/v1/rooms/<room_id> -- details contains avatar. List does not have it.
# # https://github.com/element-hq/synapse/blob/develop/docs/admin_api/rooms.md

# def get_all_groups_from_messenger(base_url: str, access_token: str, limit: int = 10) -> List[dict]:

#     url = f"{base_url}/_synapse/admin/v1/rooms"

    
#     # Set up headers with the access token
#     headers = {
#         "Authorization": f"Bearer {access_token}"
#     }

#     # Initialize variables for pagination
#     all_rooms = []
#     params = {
#         "from": 0,   # Start from the beginning
#         "limit": limit, # Fetch 'limit' rooms at a time
#     }

#     # Loop to paginate through all rooms
#     try:
#         while True:
#             # Send the GET request
#             response = requests.get(url, headers=headers, params=params)
            
#             # Check if the request was successful
#             if response.status_code >= 200 and response.status_code < 300:
#                 # Parse the response data
#                 rooms_data = response.json()
#                 rooms = rooms_data.get('rooms', [])
                
#                 # If no rooms are returned, break the loop
#                 if not rooms:
#                     break
                
#                 # Add the current batch of rooms to the list
#                 all_rooms.extend(rooms)
                
#                 # Update the 'from' parameter to get the next batch of rooms
#                 params['from'] += limit
#             else:
#                 logger.error(f"Failed to retrieve rooms: {response.status_code} - {response.text}")
#                 break
#     except Exception as e:
#         logger.exception("An unexpected error occurred while fetching rooms.")
#     print(all_rooms)
#     print(response.status_code)
#     return all_rooms


# load_dotenv()
# access_token_new = os.getenv("ADMIN_ACCESS_TOKEN")
# print(access_token_new)
# get_all_groups_from_messenger(base_url="https://messenger.b1.shuwantech.com", access_token=access_token_new)

# # get_all_groups_from_messenger(base_url="https://messenger.b1.shuwantech.com", access_token="syt_YWRtaW4_cwYRzGbxzOnMtmVqVSxx_3qUYPl")


# # syt_YWRtaW4_gMTsSJZBrdvPETTwsBlW_21Id5N