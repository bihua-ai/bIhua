from typing import List
import requests
from bihua_one_star import Star
from messenger_resident import Resident, ResidentSettings
import messenger_resident, utilities
from status_definitions import CrudStatus
from bihua_logging import get_logger

logger = get_logger()

def get_all_residents_from_messenger(base_url, access_token, limit=10) -> List[dict]:
    """
    Fetches all users from the Synapse server using the admin API.

    Args:
    - base_url (str): The base URL of your Synapse server (e.g., https://your-synapse-server).
    - access_token (str): The access token for authenticating the request.
    - limit (int): Number of users to fetch per request (default is 10).

    Returns:
    - List of all users retrieved from the API.
    """
    
    # Define the base API endpoint
    url = f"{base_url}/_synapse/admin/v2/users"
    
    # Set up headers with the access token
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Initialize variables for pagination
    all_users = []
    params = {
        "from": 0,   # Start from the beginning
        "limit": limit, # Fetch 'limit' users at a time
        "guests": "false"  # Exclude guest users
    }

    # Loop to paginate through all users
    while True:
        # Send the GET request
        response = requests.get(url, headers=headers, params=params)
        
        # Check if the request was successful
        if response.status_code >= 200 and response.status_code < 300:
            # Parse the response data
            users_data = response.json()
            users = users_data.get('users', [])
            
            # If no users are returned, break the loop
            if not users:
                break
            
            # Add the current batch of users to the list
            all_users.extend(users)
            
            # Update the 'from' parameter to get the next batch of users
            params['from'] += limit
        else:
            print(f"Failed to retrieve users: {response.status_code} - {response.text}")
            break
    return all_users

# al_users =
# [
#     {
#         'name': '@admin:messenger.b1.shuwantech.com',
#         'user_type': None,
#         'is_guest': False,
#         'admin': True,
#         'deactivated': False,
#         'shadow_banned': False,
#         'displayname': 'admin',
#         'avatar_url': None,
#         'creation_ts': 1731660775000,
#         'approved': True,
#         'erased': False,
#         'last_seen_ts': 1732616169123,
#         'locked': False
#     },
#     {
#         'name': '@user1:messenger.b1.shuwantech.com',
#         'user_type': None,
#         'is_guest': False,
#         'admin': True,
#         'deactivated': False,
#         'shadow_banned': False,
#         'displayname': 'user1',
#         'avatar_url': None,
#         'creation_ts': 1731661452000,
#         'approved': True,
#         'erased': False,
#         'last_seen_ts': 1731681105233,
#         'locked': False
#     }
# ]

def map_and_save_residents_settings(_residents_json_list: List[dict])->CrudStatus:
    try:
        for _resident_json in _residents_json_list:
            # Map the resident data to the ResidentSettings model
            username, servername = utilities.split_resident_id(_resident_json.get('name'))
            if _resident_json.get('avatar_url') is not None:
                avatar_url = utilities.convert_mxc_to_url(_resident_json.get('avatar_url'))
            else:
                avatar_url = ""
            _resident = Resident(_resident_json.get('name'))
            _resident_settings = ResidentSettings(
                resident_id=_resident_json.get('name'),
                username=username,
                display_name=_resident_json.get('displayname'),
                avatar_http_url=avatar_url,
                role='admin' if _resident_json.get('admin') else 'user',
                agent="agent", # if needed, change to line by line update, so we can set to human. Now we do not need it because we check id instead of agent or not when processing message for reply.
                state='active' if not _resident_json.get('deactivated') else 'inactive',
                last_login_timestamp_ms=_resident_json.get('last_seen_ts', 0),
                last_sync_timestamp_ms=0
            )
            _resident.settings = _resident_settings
            messenger_resident.resident_settings_save(_resident_settings)
    except Exception as e:
        logger.exception
        

# collect resident list from messenger, generate resident jsons and save to right location
def collect_and_save_residents_settings() -> CrudStatus:
    try:
        _star = Star()

        resident_data_collected = get_all_residents_from_messenger(_star.messenger_server_url, _star.messenger_admin_access_token)
        map_and_save_residents_settings(resident_data_collected)
    except Exception as e:
        logger.exception

    




get_all_residents_from_messenger("https://messenger.b1.shuwantech.com", "syt_YWRtaW4_AHErjhIlnyrmtLGcteez_1Xqm6W")