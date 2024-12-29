from typing import List
import requests
from bihua_one_star import Star
from messenger_group import Group, GroupSettings
import utilities, messenger_group
from status_definitions import CrudStatus
from bihua_logging import get_logger

logger = get_logger()

# all_rooms = 
# [
#   {
#     "room_id": "!IrwcvKRWDxTHuwwtMi:messenger.b1.shuwantech.com",
#     "name": "room1",
#     "canonical_alias": "#room1:messenger.b1.shuwantech.com",
#     "joined_members": 2,
#     "joined_local_members": 2,
#     "version": "10",
#     "creator": "@admin:messenger.b1.shuwantech.com",
#     "encryption": null,
#     "federatable": true,
#     "public": true,
#     "join_rules": "public",
#     "guest_access": null,
#     "history_visibility": "shared",
#     "state_events": 8,
#     "room_type": null
#   }
# ]


def get_all_groups_from_messenger(base_url: str, access_token: str, limit: int = 10) -> List[dict]:


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
    try:
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
                logger.error(f"Failed to retrieve rooms: {response.status_code} - {response.text}")
                break
    except Exception as e:
        logger.exception("An unexpected error occurred while fetching rooms.")
    return all_rooms


def map_and_save_groups_settings(_groups_json_list: List[dict]):
    try:
        for _group_json in _groups_json_list:
            try:
                groupname, servername = utilities.split_group_id(_group_json.get("name"))
                if _groups_json_list.get('avatar_url') is not None:
                    avatar_url = utilities.convert_mxc_to_url(_group_json.get('avatar_url'))
                else:
                    avatar_url = ""
                group_id = _group_json.get("name")
                # Map fields from _group_json to GroupSettings
                _group = Group(group_id)
                _group.group_settings_update(
                    group_id=_group_json.get("name"),
                    avatar_http_url=avatar_url,
                    groupname=_group_json.get("name"),
                    alias=_group_json.get("alias"),
                    size=_group_json.get("size", 1),  # Default to 1 if not provided
                    public=_group_json.get("public", True),  # Default to True if not provided
                    encryption=_group_json.get("encryption", False),  # Default to False if not provided
                )
                
                
                # Save the settings
                messenger_group.group_settings_create_and_save(_group.settings)
                logger.info(f"Successfully saved settings for group: {_group_json.get('name')}")
            
            except KeyError as e:
                logger.error(f"Missing key in group data: {e}, Data: {_group_json}")
            except Exception as e:
                logger.exception(f"Error processing group data: {_group_json}")
    except Exception as e:
        logger.exception("An unexpected error occurred while mapping and saving group settings.")



def collect_and_save_groups_settings() -> CrudStatus:
    """
    Collects and saves group settings.

    Returns:
    - CrudStatus: The status of the operation.
    """
    try:
        _star = Star()
        group_data_collected = get_all_groups_from_messenger(
            _star.messenger_server_url, _star.messenger_admin_access_token
        )
        map_and_save_groups_settings(group_data_collected)
        logger.info("Successfully collected and saved group settings.")
        return CrudStatus.SUCCESS
    except Exception as e:
        logger.exception("An unexpected error occurred in collect_and_save_groups_settings.")
        return CrudStatus.EXCEPTION
