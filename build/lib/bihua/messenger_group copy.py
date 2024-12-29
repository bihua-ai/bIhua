from pydantic import BaseModel
import os, requests, json
from bihua_one_star import Star
import bihua_one_star as bihua_one_star
from typing import Optional, Dict, Tuple, Any, List
from bihua_logging import get_logger
import utilities
from status_definitions import CrudStatus

# Logger setup
logger = get_logger()

class GroupSettings(BaseModel):
    group_id: str
    avatar_http_url: str = None
    groupname: str = None
    alias: str = None
    size: int = 1  # number of members
    public: bool = True  # public or private
    encryption: str = None  # Optional encryption settings
    homeserver_url: str = None
    profile_text_path: str = None
    profile_json_path: str = None

class Group:
    group_star: Star = None
    settings: GroupSettings = None
    # encryption: Optional[Dict[str, Any]] = None

    def __init__(self, group_id: str):
        self.group_id = group_id
        self.group_star = Star()

        # Attempt to load the existing settings
        load_status, self.settings = group_settings_load(group_id)
        if load_status == CrudStatus.SUCCESS:
            return
        else:
            logger.info(f"No existing settings found for {group_id}, creating new settings.")
            self.create_default_settings(group_id) # create and assign created settings to self.settings.
            profile_text = "Please enter agent profile text here..."
            self.group_profile_create_or_update(profile_text=profile_text)

    def create_default_settings(self, group_id: str) -> CrudStatus:
        """
        Creates default settings for the given group and saves them.
        
        Returns:
            CrudStatus: SUCCESS if settings are created successfully, EXCEPTION if an error occurs
        """
        try:
            # Split group_id to get groupname and servername
            groupname, servername = utilities.split_group_id(group_id)
            
            # Define file paths for profile text and JSON
            profile_text_path = os.path.join(self.group_star.star_groups_data_home, group_id, self.group_star.group_profile_subfolder, f"{group_id}.txt")
            profile_json_path = os.path.join(self.group_star.star_groups_data_home, group_id, self.group_star.group_profile_subfolder, f"{group_id}.json")

            # Log the start of the settings creation process
            logger.info(f"Creating default settings for group {group_id}...")

            # Call the group_settings_create_and_save function to create and save settings
            create_status, self.settings = group_settings_create_and_save(
                group_id=group_id,
                avatar_http_url="",
                groupname=groupname,
                alias=groupname,
                size=1,
                public=True,
                encryption=None,
                homeserver_url=self.group_star.messenger_server_url,
                profile_text_path=profile_text_path,
                profile_json_path=profile_json_path
            )

            if create_status == CrudStatus.SUCCESS:
                logger.info(f"Default settings for group {group_id} created successfully.")
                return CrudStatus.SUCCESS
            else:
                logger.error(f"Error creating default settings for group {group_id}.")
                return CrudStatus.ERROR
        except Exception as e:
            # Log the error with a message
            logger.error(f"Exception creating default settings for group {group_id}: {e}")
            return CrudStatus.EXCEPTION

    def group_settings_update(self, **updates) -> CrudStatus:
        """
        Updates the attributes of the GroupSettings instance.
        The `**updates` argument allows for passing dynamic key-value pairs.
        """
        try:
            logger.info(f"Updating group settings for {self.group_id} with updates: {updates}")
            
            # Load existing group_settings
            load_status, self.settings = group_settings_load(self.group_id)
            if load_status != CrudStatus.SUCCESS:
                logger.error(f"Group settings for {self.group_id} could not be loaded.")
                return CrudStatus.ERROR

            # Apply updates
            for field, value in updates.items():
                if hasattr(self.settings, field):
                    setattr(self.settings, field, value)
                else:
                    logger.warning(f"{field} is not a valid attribute of GroupSettings.")

            # After updating, save the group_settings
            save_status = group_settings_save(self.settings)
            if save_status == CrudStatus.SUCCESS:
                logger.info(f"Successfully updated and saved group settings for {self.group_id}.")
                return CrudStatus.SUCCESS
            else:
                logger.error(f"Failed to save updated group settings for {self.group_id}.")
                return CrudStatus.ERROR
            
        except Exception as e:
            # Log any exception that occurs
            logger.error(f"Unexpected error while updating group settings for {self.group_id}: {e}", exc_info=True)
            return CrudStatus.EXCEPTION
        
    def group_profile_create_or_update(self, profile_text: str) -> CrudStatus:
        """
        Saves the group profile text to the specified file path. 
        Returns a CrudStatus indicating the operation's result.
        """
        try:
            with open(self.settings.profile_text_path, 'w') as file:
                file.write(profile_text)
                logger.info(f"Group profile successfully saved to {self.settings.profile_text_path}.")
                return CrudStatus.SUCCESS
        except Exception as e:
            logger.exception(f"Failed to save group profile to {self.settings.profile_text_path}: {e}")
            return CrudStatus.EXCEPTION


    def group_profile_load(self) -> Tuple[CrudStatus, Optional[str]]:
        """
        Loads the group profile text from the specified file path.
        Returns a tuple containing a CrudStatus and the profile text (or None if an error occurs).
        """
        try:
            with open(self.settings.profile_text_path, 'r') as file:
                profile_text = file.read()
                logger.info(f"Group profile successfully loaded from {self.settings.profile_text_path}.")
                return CrudStatus.SUCCESS, profile_text
        except FileNotFoundError:
            logger.info(f"Group profile file not found at {self.settings.profile_text_path}. Returning an empty profile.")
            return CrudStatus.ERROR, None
        except Exception as e:
            logger.exception(f"Failed to load group profile from {self.settings.profile_text_path}: {e}")
            return CrudStatus.EXCEPTION, None

def group_settings_create_and_save(
    group_id: str,
    avatar_http_url: str = None,
    groupname: str = None,
    alias: str = None,
    size: int = 1,
    public: bool = False,
    encryption: str = None,
    homeserver_url: str = None,
    profile_text_path: str = None,
    profile_json_path: str = None
) -> Tuple[CrudStatus, Optional[GroupSettings]]:
    try:
        # Initialize GroupSettings instance
        group_settings = GroupSettings(
            group_id=group_id,
            avatar_http_url=avatar_http_url,
            groupname=groupname,
            alias=alias,
            size=size,
            public=public,
            encryption=encryption,
            homeserver_url=homeserver_url,
            profile_text_path=profile_text_path,
            profile_json_path=profile_json_path
        )
        
        # Initialize Star to retrieve paths
        _star = Star()
        setting_json_file_location = os.path.join(_star.star_groups_data_home, group_id, _star.group_profile_subfolder)
        setting_json_file = os.path.join(setting_json_file_location, f"{group_id}.json")

        # Check if directory exists; create if not
        if not os.path.exists(setting_json_file_location):
            logger.debug(f"Creating directory: {setting_json_file_location}")
            os.makedirs(setting_json_file_location)

        # Write to the settings JSON file
        with open(setting_json_file, 'w') as f:
            f.write(group_settings.model_dump_json())
        
        # Log the success and return CrudStatus.SUCCESS
        logger.info(f"Settings for group {group_id} saved successfully at {setting_json_file}.")
        return CrudStatus.SUCCESS, group_settings

    except FileNotFoundError as fnf_error:
        logger.error(f"FileNotFoundError while saving settings for {group_id}: {fnf_error}")
        return CrudStatus.ERROR, None
    except PermissionError as perm_error:
        logger.error(f"PermissionError while saving settings for {group_id}: {perm_error}")
        return CrudStatus.ERROR, None
    except Exception as e:
        # Catch all other exceptions
        logger.error(f"Unexpected error saving settings for {group_id}: {e}", exc_info=True)
        return CrudStatus.EXCEPTION, None

def group_settings_save(group_settings: GroupSettings) -> CrudStatus:
    if group_settings is None:
        logger.error("Attempted to save None as group settings.")
        return CrudStatus.ERROR

    try:
        _star = Star()
        setting_json_file_location = os.path.join(_star.star_groups_data_home, group_settings.group_id, _star.group_profile_subfolder)
        setting_json_file = os.path.join(setting_json_file_location, f"{group_settings.group_id}.json")

        # Create directory if it doesn't exist
        if not os.path.exists(setting_json_file_location):
            os.makedirs(setting_json_file_location)

        # Write the updated group settings to the JSON file
        with open(setting_json_file, 'w') as f:
            f.write(group_settings.model_dump_json())
        
        logger.info(f"Group settings for {group_settings.group_id} saved successfully.")
        return CrudStatus.SUCCESS

    except Exception as e:
        logger.error(f"Error saving group settings for {group_settings.group_id}: {e}")
        return CrudStatus.EXCEPTION

def group_settings_load(group_id: str) -> Tuple[CrudStatus, Optional[GroupSettings]]:
    """
    Loads the group settings from the file system.
    
    Returns a tuple of:
    - CrudStatus: indicates the result (SUCCESS, ERROR, EXCEPTION)
    - GroupSettings or None: the loaded group settings if successful, or None if not
    """
    try:
        logger.info(f"Loading group settings for {group_id}...")
        
        # Create instance of Star
        _star = Star()
        setting_json_file_location = os.path.join(_star.star_groups_data_home, group_id, _star.group_profile_subfolder)
        setting_json_file = os.path.join(setting_json_file_location, f"{group_id}.json")

        # Check if settings file exists
        if os.path.exists(setting_json_file):
            with open(setting_json_file, 'r') as f:
                setting_json = json.load(f)
                if not setting_json: # setting_json = {} - empty file
                    logger.warning(f"Loaded empty settings for {group_id}.")
                    return CrudStatus.ERROR, None

            # Create GroupSettings instance from loaded JSON
            group_settings = GroupSettings(**setting_json)
            logger.info(f"Successfully loaded group settings for {group_id}.")
            return CrudStatus.SUCCESS, group_settings

        else:
            logger.info(f"Group settings file not found for {group_id}.")
            return CrudStatus.ERROR, None

    except Exception as e:
        logger.exception(f"Exception when loading group settings for {group_id}: {e}")
        return CrudStatus.EXCEPTION, None
    

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

# GET /_synapse/admin/v1/rooms/<room_id> -- details contains avatar. List does not have it.
# GET /_synapse/admin/v1/rooms
# https://github.com/element-hq/synapse/blob/develop/docs/admin_api/rooms.md


def get_all_groups_from_messenger(base_url: str, access_token: str, limit: int = 10) -> List[dict]:
    """
    Fetches all room groups from the messenger, including detailed information for each room.

    Args:
        base_url (str): The base URL of the messenger API.
        access_token (str): Access token for authentication.
        limit (int): Number of rooms to fetch per batch. Default is 10.

    Returns:
        List[dict]: A list containing detailed information about all rooms.
    """
    url = f"{base_url}/_synapse/admin/v1/rooms"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Initialize variables for pagination and room details
    all_rooms = []
    params = {
        "from": 0,
        "limit": limit
    }

    try:
        # Fetch paginated list of rooms
        while True:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code >= 200 and response.status_code < 300:
                rooms_data = response.json()
                rooms = rooms_data.get('rooms', [])
                
                if not rooms:  # No more rooms to fetch
                    break
                
                all_rooms.extend(rooms)
                params['from'] += limit
            else:
                logger.error(f"Failed to retrieve rooms: {response.status_code} - {response.text}")
                break
        
        # Fetch details for each room
        detailed_rooms = []
        for room in all_rooms:
            room_id = room.get('room_id')
            if not room_id:
                logger.warning(f"Room data missing 'room_id': {room}")
                continue
            
            room_details_url = f"{base_url}/_synapse/admin/v1/rooms/{room_id}"
            room_details_response = requests.get(room_details_url, headers=headers)
            
            if room_details_response.status_code >= 200 and room_details_response.status_code < 300:
                room_details = room_details_response.json()
                detailed_rooms.append(room_details)
            else:
                logger.error(f"Failed to retrieve room details for {room_id}: {room_details_response.status_code} - {room_details_response.text}")
        
        return detailed_rooms

    except Exception as e:
        logger.exception("An unexpected error occurred while fetching rooms.")
        return []



def map_and_save_groups_settings(detailed_rooms: List[dict]):
    """
    Maps the detailed room data to group settings and saves it.

    Args:
        detailed_rooms (List[dict]): List of detailed room data.

    """
    try:
        for room in detailed_rooms:
            try:
                # Extract groupname and servername from the room ID
                room_id = room.get("room_id")
                if not room_id:
                    logger.warning(f"Room data missing 'room_id': {room}")
                    continue
                
                # Process avatar URL if available
                avatar_url = utilities.convert_mxc_to_url(room.get("avatar_url")) if room.get("avatar_url") else ""
                
                # Create and map the group
                group = Group(room_id)
                group.group_settings_update(
                    group_id=room_id,
                    avatar_http_url=avatar_url,
                    groupname=room.get("name"),
                    alias=room.get("canonical_alias", ""),  # Use canonical_alias if available
                    size=room.get("joined_members", 1),  # Use joined_members as size
                    public=room.get("public", True),  # Default to True for public
                    encryption=room.get("encryption") if room.get("encryption") else "",
                )
                
                # Save the group settings
                # group_settings_create_and_save(group.settings)
                logger.info(f"Successfully saved settings for room: {room_id}")
            
            except KeyError as e:
                logger.error(f"Missing key in room data: {e}, Data: {room}")
            except Exception as e:
                logger.exception(f"Error processing room data: {room}")
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
    
def fetch_group_data_paths_from_env():
    pass

def generate_group_json_list():
    """
    Generates a list of group JSON data and saves it to a file.
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Fetch data paths from environment
        star_groups_data_home, group_profile_subfolder, group_list_json_path = fetch_group_data_paths_from_env()
        logger.debug("Fetched group data paths from environment variables.")

        group_list = []

        # Iterate over group directories
        for group_id in os.listdir(star_groups_data_home):
            group_profile_full_path = os.path.join(star_groups_data_home, group_id, group_profile_subfolder)
            if os.path.isdir(group_profile_full_path) and group_id.startswith("!"):
                try:
                    with open(os.path.join(group_profile_full_path, f"{group_id}.json"), 'r') as f:
                        group_json = json.load(f)
                        group_list.append(group_json)
                        logger.debug(f"Added group profile from {group_profile_full_path}.")
                except json.JSONDecodeError as json_err:
                    logger.error(f"JSON decode error in {group_profile_full_path}: {json_err}")
                    return False
                except Exception as file_err:
                    logger.error(f"Error reading file {group_profile_full_path}: {file_err}")
                    return False

        # Save the consolidated group list
        if group_list:
            try:
                with open(group_list_json_path, 'w') as f:
                    json.dump(group_list, f, indent=4)
                logger.info(f"Group list successfully saved to {group_list_json_path}.")
            except Exception as save_err:
                logger.error(f"Error saving group list to {group_list_json_path}: {save_err}")
                return False
        else:
            logger.warning("No group profiles found to save.")
            return False

        return True
    except Exception as e:
        logger.exception("Unexpected error in generate_group_json_list.")
        return False

def append_group_json_list(group_id) -> CrudStatus:
    logger.info(f"Appending group profile with ID: {group_id} to the group JSON list.")

    try:
        star_groups_data_home, group_profile_subfolder, group_list_json_path = fetch_group_data_paths_from_env()

        # Load the existing group JSON list
        try:
            with open(group_list_json_path, 'r') as f:
                group_json_list = json.load(f)
            logger.info(f"Successfully loaded existing group JSON list from {group_list_json_path}.")
        except FileNotFoundError:
            # If the file doesn't exist, initialize an empty list
            logger.warning(f"Group list file {group_list_json_path} not found. Initializing an empty list.")
            group_json_list = []
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from group list file {group_list_json_path}: {e}")
            return CrudStatus.ERROR

        # Read the group's profile JSON data
        group_profile_path = os.path.join(star_groups_data_home, group_id, group_profile_subfolder, f"{group_id}.json")
        try:
            with open(group_profile_path, 'r') as f:
                group_json = json.load(f)
            logger.info(f"Successfully loaded group profile from {group_profile_path}.")
        except FileNotFoundError:
            logger.error(f"Group profile file {group_profile_path} not found.")
            return CrudStatus.ERROR
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from group profile {group_profile_path}: {e}")
            return CrudStatus.ERROR

        # Append the group profile to the list
        group_json_list.append(group_json)

        # Write the updated list back to the JSON file
        try:
            with open(group_list_json_path, 'w') as f:
                json.dump(group_json_list, f, indent=4)  # Use json.dump to write properly formatted JSON
            logger.info(f"Successfully updated group list in {group_list_json_path}.")
        except IOError as e:
            logger.error(f"Error writing to file {group_list_json_path}: {e}")
            return CrudStatus.ERROR

        return CrudStatus.SUCCESS

    except Exception as e:
        logger.exception(f"An unexpected error occurred while appending group profile: {e}")
        return CrudStatus.EXCEPTION


def update_group_json_list(group_id: str) -> CrudStatus:
    try:
        star_groups_data_home, group_profile_subfolder, group_list_json_path = fetch_group_data_paths_from_env()
        
        logger.info(f"Loading group list from {group_list_json_path}")
        with open(group_list_json_path, 'r') as f:
            group_json_list = json.load(f)
    except FileNotFoundError:
        logger.error(f"Group list file {group_list_json_path} not found.")
        return CrudStatus.ERROR
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from group list file {group_list_json_path}.")
        return CrudStatus.EXCEPTION

    try:
        logger.info(f"Loading updated group profile for ID {group_id}")
        updated_group_json_path = os.path.join(star_groups_data_home, group_id, group_profile_subfolder, f"{group_id}.json")
        with open(updated_group_json_path, 'r') as f:
            updated_group_json = json.load(f)
        if not updated_group_json:
            logger.warning(f"Group with ID {group_id} not found.")
            return CrudStatus.EXCEPTION
    except Exception as e:
        logger.exception(f"Unexpected error occurred while processing group data: {e}")
        return CrudStatus.ERROR

    for i, group_json in enumerate(group_json_list):
        if group_json.get('group_id') == group_id:
            logger.info(f"Updating group profile for ID {group_id}")
            group_json_list[i] = updated_group_json
            break
    else:
        logger.warning(f"Group with ID {group_id} not found in the list.")
        return CrudStatus.ERROR

    try:
        logger.info(f"Saving updated group list to {group_list_json_path}")
        with open(group_list_json_path, 'w') as f:
            json.dump(group_json_list, f, indent=4)
    except IOError as e:
        logger.error(f"Error writing to group list file {group_list_json_path}: {e}")
        return CrudStatus.EXCEPTION

    logger.info(f"Group profile for ID {group_id} updated successfully.")
    return CrudStatus.SUCCESS




# print("in resident")
# _group = Group("!admin:chat.b1.shuwantech.com")
# _group.group_settings_update(avatar_http_url = "http://test")
# print(_group.settings)


