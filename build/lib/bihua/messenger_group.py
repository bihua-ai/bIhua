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
    group_name: str = None
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

    def __init__(self, group_id: str):
        try:
            settings_status, settings = create_update_group_settings(group_id)
            if settings_status != CrudStatus.SUCCESS:
                logger.error(f"Group initialization failed for Group ID ={group_id}.")
                return None
            
            _star = Star()
            self.group_id = group_id
            self.settings = settings # created and loaded 
            self.group_star = _star
            logger.info(f"Group successfully initialized for for Group ID ={group_id}.")
        except Exception as e:
            logger.exception(f"Group initialization failed for Group ID ={group_id}.")

    def group_settings_update(self, **updates) -> CrudStatus:
        try:
            update_status, settings = group_settings_update_sync_save(self.group_id, **updates)
            if update_status == CrudStatus.SUCCESS:
                self.settings = settings
                logger.info(f"Group settings updated successfully for group ID ={self.group_id}.")
            else:
                logger.error(f"Failed to update group settings for group ID ={self.group_id}. Updates attempted: {updates}")
        except Exception as e:
            logger.exception(f"Failed to update group settings for group ID ={self.group_id}. Updates attempted: {updates}")


    # MEMBER FUNCTION
    # Profile text needs to be prepared before calling this function
    def group_text_profile_create_or_update(self, profile_text: str) -> CrudStatus:
        try:
            with open(self.settings.profile_text_path, 'w') as file:
                file.write(profile_text)
                logger.info(f"Group profile successfully saved to {self.settings.profile_text_path}.")
                return CrudStatus.SUCCESS
        except Exception as e:
            logger.exception(f"Failed to save group profile to {self.settings.profile_text_path}: {e}")
            return CrudStatus.EXCEPTION

    # MEMBER FUNCTION
    # Profile text load
    def group_text_profile_load(self) -> Tuple[CrudStatus, Optional[str]]:
        try:
            with open(self.settings.profile_text_path, 'r') as file:
                profile_text = file.read()
                logger.info(f"Group profile successfully loaded from {self.settings.profile_text_path}.")
                return CrudStatus.SUCCESS, profile_text
        except Exception as e:
            logger.exception(f"Failed to load group profile from {self.settings.profile_text_path}: {e}")
            return CrudStatus.EXCEPTION, None


# PRIVATE FUNCTION
# It is designed for other functions in this module.
def group_settings_load(group_id: str) -> Tuple[CrudStatus, Optional[GroupSettings]]:
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


# PRIVATE FUNCTION
# Designed to be used by other functions in this module.
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


# PRIVATE FUNCTION
# Designed for other functions in this module.
def group_settings_update_sync_save(group_id:str, **updates) -> Tuple[CrudStatus, GroupSettings]:
    try:
        # Load existing group_settings
        load_status, settings = group_settings_load(group_id)
        if load_status != CrudStatus.SUCCESS:
            logger.info(f"Group settings for {group_id} could not be loaded.")
            _status, settings = create_update_group_settings(group_id) # data from messenger is synced
            if _status != CrudStatus.SUCCESS:
                return CrudStatus.EXCEPTION, None
            else:
                logger.info(f"Group settings for {group_id} created.")
        else:
            logger.info(f"Group settings for {group_id} is loaded.")
        # Apply updates
        for field, value in updates.items():
            if hasattr(settings, field):
                setattr(settings, field, value)
            else:
                logger.error(f"{field} is not a valid attribute of GroupSettings.")
        
        # After updating the attributes, save the group settings
        group_settings_save(settings)
        # sync data from group
        create_update_group_settings(group_id) # This is called twice if group_settings_load failed. Code is simpler. If it causes performance issues. we will optimize in thsi function.
        update_group_json_list(group_id)


    except Exception as e:
        logger.exception(f"Exception occurred in residetn setting update: {e}")


# PRIVATE FUNCTION
# Designed for internal use.
# Add profile json to pjson list of profiles.
def append_group_json_list(group_id) -> CrudStatus:
    try:
        logger.info(f"Appending group profile with ID: {group_id} to the group JSON list.")
        _star = Star()

        # Load the existing group JSON list
        with open(_star.group_list_json_path, 'r') as f:
            group_json_list = json.load(f)
        logger.info(f"Successfully loaded existing group JSON list from {_star.group_list_json_path}.")

        # Load the group's profile json
        group_profile_path = os.path.join(_star.star_groups_data_home, group_id, _star.group_profile_subfolder, f"{group_id}.json")
        with open(group_profile_path, 'r') as f:
            group_json = json.load(f)
        logger.info(f"Successfully loaded group profile from {group_profile_path}.")

        # Append the group profile to the list
        group_json_list.append(group_json)

        # Write the updated list back to the JSON file
        with open(_star.group_list_json_path, 'w') as f:
            json.dump(group_json_list, f, indent=4)  # Use json.dump to write properly formatted JSON
        logger.info(f"Successfully appended group list in {_star.group_list_json_path}.")
        return CrudStatus.SUCCESS

    except Exception as e:
        logger.exception(f"An unexpected error occurred while appending group profile: {e}")
        return CrudStatus.EXCEPTION


# PRIVATE FUNCTION
# Designed for internal use.
# Update profile json to pjson list of profiles.
def update_group_json_list(group_id: str) -> CrudStatus:
    try:
        logger.info(f"Appending group profile with ID: {group_id} to the group JSON list.")
        _star = Star()

        # Load the existing group JSON list
        with open(_star.group_list_json_path, 'r') as f:
            group_json_list = json.load(f)
        logger.info(f"Successfully loaded existing group JSON list from {_star.group_list_json_path}.")

        # Load the group's profile json
        group_profile_path = os.path.join(_star.star_groups_data_home, group_id, _star.group_profile_subfolder, f"{group_id}.json")
        with open(group_profile_path, 'r') as f:
            updated_group_json = json.load(f)
        logger.info(f"Successfully loaded group profile from {group_profile_path}.")

        # Update the group profile to the list
        for i, group_json in enumerate(group_json_list):
            if group_json.get('group_id') == group_id:
                logger.info(f"Updating group profile for ID {group_id}")
                group_json_list[i] = updated_group_json
                break

        # Write the updated list back to the JSON file
        with open(_star.group_list_json_path, 'w') as f:
            json.dump(group_json_list, f, indent=4)  # Use json.dump to write properly formatted JSON
        logger.info(f"Successfully updated group list in {_star.group_list_json_path}.")
        return CrudStatus.SUCCESS

    except Exception as e:
        logger.exception(f"An unexpected error occurred while updating group profile: {e}")
        return CrudStatus.EXCEPTION


# PRIVATE FUNCTION
# This is used by other functions in this module.
def get_group_data_from_messenger(group_id: str) -> Tuple[CrudStatus, Optional[dict]]:
    try:
        _star = Star()
        headers = {"Authorization": f"Bearer {_star.messenger_admin_access_token}"}
        url = f"{_star.messenger_server_url}/_synapse/admin/v1/rooms/{group_id}"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code >= 200 and response.status_code < 300:  # Cleaner HTTP status check
            logger.info(f"Successfully retrieved data for group ID: {group_id}")
            return CrudStatus.SUCCESS, response.json()
        
        logger.error(
            f"Failed to retrieve data for group ID: {group_id}. "
            f"HTTP Status: {response.status_code}, Response: {response.text}"
        )
        return CrudStatus.ERROR, None
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred while retrieving data for group ID: {group_id}."
        )
        return CrudStatus.EXCEPTION, None



    # try:
    #     _star = Star()
    #     headers = {"Authorization": f"Bearer {_star.messenger_admin_access_token}"}
    #     url = f"{_star.messenger_server_url}/_synapse/admin/v1/rooms/{group_id}"
    #     response = requests.get(url, headers=headers)
    #     if response.status_code >= 200 and response.status_code < 300:
    #         return response.json()
    # except Exception as e:
    #     logger.exception(f"")
    


    # url = f"{base_url}/_synapse/admin/v1/rooms"
    # headers = {
    #     "Authorization": f"Bearer {access_token}"
    # }
    # room_details_url = f"{base_url}/_synapse/admin/v1/rooms/{room_id}"
    # room_details_response = requests.get(room_details_url, headers=headers)
    
    # if room_details_response.status_code >= 200 and room_details_response.status_code < 300:
    #     room_details = room_details_response.json()
    #     detailed_rooms.append(room_details)
    # else:
    #     logger.error(f"Failed to retrieve room details for {room_id}: {room_details_response.status_code} - {room_details_response.text}")

# PRIVATE FUNCTION
# Designed for internal use.
def create_update_group_settings(group_id: str) -> Tuple[CrudStatus, GroupSettings]:
    # get data from messenger server
    create_status, group_settings_json = get_group_data_from_messenger(group_id=group_id)
    if create_status != CrudStatus.SUCCESS:
        logger.error(f"Failed to retrieve data of group {group_id} from messenger server.")
        return CrudStatus.ERROR, None
    
    # prepare local profile json and txt
    _star = Star
    try:
        # prepare profile text
        profile_text_path = os.path.join(_star.star_groups_data_home, group_id, _star.group_profile_subfolder, f"{group_id}.txt")
        profile_json_path = os.path.join(_star.star_groups_data_home, group_id, _star.group_profile_subfolder, f"{group_id}.json")

        os.makedirs(os.path.dirname(profile_text_path), exist_ok=True) # both txt and json are in the same directory, check once
        if not os.path.exists(profile_text_path):
            profile_text = "Please enter agent profile text here..."
            with open(profile_text_path, 'w') as file:
                file.write(profile_text)  # Create an empty file
        
        # prepare profile json
        # if not os.path.exists(profile_json_path):
        #     with open(profile_json_path, 'w') as file:
        #         file.write("{}")  # Create an empty JSON file

        # create or update settings: either None or proper content
        load_status, group_settings = group_settings_load(group_id=group_id)
        if load_status != CrudStatus.SUCCESS or (load_status == CrudStatus.SUCCESS and group_settings is None): # needs to create new
            avatar_url = utilities.convert_mxc_to_url(group_settings_json.get("avatar")) if group_settings_json.get("avatar") else ""
            group_settings = GroupSettings()
            group_settings.group_id = group_id
            group_settings.avatar_http_url = avatar_url
            group_settings.group_name = group_settings_json.get("name")
            group_settings.alias = group_settings_json.get("canonical_alias")
            group_settings.size = group_settings_json.get("joined_members")
            group_settings.public = group_settings_json.get("public")
            group_settings.encryption = group_settings_json.get("encryption")
            group_settings.homeserver_url = _star.messenger_server_url
            group_settings.profile_text_path = profile_text_path
            group_settings.profile_json_path = profile_json_path

            group_settings_save(group_settings)
            append_group_json_list(group_id)
            logger.info(f"Created and saved settings for {group_id}")

        else: # just update content from messenger
            avatar_url = utilities.convert_mxc_to_url(group_settings_json.get("avatar")) if group_settings_json.get("avatar") else ""
   
            group_settings.group_id = group_id
            group_settings.avatar_http_url = avatar_url
            group_settings.group_name = group_settings_json.get("name")
            group_settings.alias = group_settings_json.get("canonical_alias")
            group_settings.size = group_settings_json.get("joined_members")
            group_settings.public = group_settings_json.get("public")
            group_settings.encryption = group_settings_json.get("encryption")
            # group_settings.homeserver_url = _star.messenger_server_url
            # group_settings.profile_text_path = profile_text_path
            # group_settings.profile_json_path = profile_json_path

            group_settings_save(group_settings)
            update_group_json_list(group_id)
            logger.info(f"Updated and saved settings for {group_id}")

        return CrudStatus.SUCCESS, group_settings

    except Exception as e:
        logger.exception(f"Exception ocurred in create_update_group_settings for {group_id}.")
        return CrudStatus.EXCEPTION, None





# def group_settings_create_and_save(
#     group_id: str,
#     avatar_http_url: str = None,
#     groupname: str = None,
#     alias: str = None,
#     size: int = 1,
#     public: bool = False,
#     encryption: str = None,
#     homeserver_url: str = None,
#     profile_text_path: str = None,
#     profile_json_path: str = None
# ) -> Tuple[CrudStatus, Optional[GroupSettings]]:
#     try:
#         # Initialize GroupSettings instance
#         group_settings = GroupSettings(
#             group_id=group_id,
#             avatar_http_url=avatar_http_url,
#             groupname=groupname,
#             alias=alias,
#             size=size,
#             public=public,
#             encryption=encryption,
#             homeserver_url=homeserver_url,
#             profile_text_path=profile_text_path,
#             profile_json_path=profile_json_path
#         )
        
#         # Initialize Star to retrieve paths
#         _star = Star()
#         setting_json_file_location = os.path.join(_star.star_groups_data_home, group_id, _star.group_profile_subfolder)
#         setting_json_file = os.path.join(setting_json_file_location, f"{group_id}.json")

#         # Check if directory exists; create if not
#         if not os.path.exists(setting_json_file_location):
#             logger.debug(f"Creating directory: {setting_json_file_location}")
#             os.makedirs(setting_json_file_location)

#         # Write to the settings JSON file
#         with open(setting_json_file, 'w') as f:
#             f.write(group_settings.model_dump_json())
        
#         # Log the success and return CrudStatus.SUCCESS
#         logger.info(f"Settings for group {group_id} saved successfully at {setting_json_file}.")
#         return CrudStatus.SUCCESS, group_settings

#     except FileNotFoundError as fnf_error:
#         logger.error(f"FileNotFoundError while saving settings for {group_id}: {fnf_error}")
#         return CrudStatus.ERROR, None
#     except PermissionError as perm_error:
#         logger.error(f"PermissionError while saving settings for {group_id}: {perm_error}")
#         return CrudStatus.ERROR, None
#     except Exception as e:
#         # Catch all other exceptions
#         logger.error(f"Unexpected error saving settings for {group_id}: {e}", exc_info=True)
#         return CrudStatus.EXCEPTION, None






    

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


# Get data from messenger, update every group's json profile.
def sync_and_save_groups_settings() -> CrudStatus:
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
    

def generate_group_json_list():
    try:
        _star = Star()
        # Fetch data paths from environment
        logger.debug("Fetched group data paths from environment variables.")

        group_list = []

        # Iterate over group directories
        for group_id in os.listdir(_star.star_groups_data_home):
            group_profile_full_path = os.path.join(_star.star_groups_data_home, group_id, _star.group_profile_subfolder)
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
                with open(_star.group_list_json_path, 'w') as f:
                    json.dump(group_list, f, indent=4)
                logger.info(f"Group list successfully saved to {_star.group_list_json_path}.")
            except Exception as save_err:
                logger.error(f"Error saving group list to {_star.group_list_json_path}: {save_err}")
                return False
        else:
            logger.warning("No group profiles found to save.")
            return False

        return True
    except Exception as e:
        logger.exception("Unexpected error in generate_group_json_list.")
        return False


# PUBLIC FUNCTION
# 
def get_group_list() -> tuple[CrudStatus, dict]:
    """Get the resident list from the JSON file."""
    _star = Star()
    file_path = _star.resident_list_json_path
    try:
        logger.info(f"Attempting to load resident list from {file_path}")
        status, data = utilities.read_json_file(file_path)
        
        if status == CrudStatus.SUCCESS:
            logger.info(f"Successfully loaded resident list from {file_path}")
            return CrudStatus.SUCCESS, data
        
        logger.error(f"Failed to load resident list from {file_path}. Status: {status}")
        return CrudStatus.ERROR, {"error": "Failed to load resident list"}

    except Exception as e:
        logger.error(f"Exception occurred while getting resident list from {file_path}: {e}")
        return CrudStatus.EXCEPTION, {"error": f"Exception: {e}"}
    

# PUBLIC FUNCTION
# Called by Fast API to delete an upladed file.
def delete_group_document(group_id: str, file_name: str) -> Tuple[CrudStatus, Optional[str]]:
    try:
        # Initialize group object
        _star = Star()
        # Construct the full path to the document
        file_full_path = os.path.join(
            _star.star_groups_data_home, 
            group_id,
            _star.group_document_subfolder, 
            file_name
        )

        logger.info(f"Attempting to delete document: {file_full_path}")

        # Check if the file exists before attempting deletion
        if os.path.exists(file_full_path):
            os.remove(file_full_path)
            logger.info(f"Document {file_name} deleted successfully for group {group_id}")
            return CrudStatus.SUCCESS, "Deleted successfully"
        else:
            logger.warning(f"Document {file_name} not found for group {group_id}")
            return CrudStatus.ERROR, "Document does not exist"
    
    except Exception as e:
        logger.error(f"Error deleting document for group {group_id}. Exception: {e}", exc_info=True)
        return CrudStatus.EXCEPTION, "Internal server error"


def get_uploaded_group_document_names(group_id: str) -> Any:
    try:
        logger.info(f"Loading document for group: {group_id}")
        
        # Initialize the group object and log the path
        _star = Star()
        group_home_path = os.path.join(
            _star.star_groups_data_home,
            group_id
        )
        
        logger.debug(f"group home path: {group_home_path}")
        
        # Define folders to select and whether to exclude hidden files
        selected_folders = [_star.group_document_subfolder]
        exclude_hidden = True  # Set to False to include hidden files/folders
        
        # Load the directory tree and handle success
        logger.info(f"Attempting to load documents...")
        counter, tree_data = utilities.load_directory_tree(group_home_path, selected_folders, exclude_hidden)
        
        logger.info(f"Successfully loaded documents with {counter} items.")
        return CrudStatus.SUCCESS, tree_data

    except Exception as e:
        logger.exception(f"An unexpected error occurred while loading the documents for {group_id}: {e}")
        return CrudStatus.EXCEPTION, str(e)  # Return exception status with the exception message




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

# {
#   "room_id": "!mscvqgqpHYjBGDxNym:matrix.org",
#   "name": "Music Theory",
#   "avatar": "mxc://matrix.org/AQDaVFlbkQoErdOgqWRgiGSV",
#   "topic": "Theory, Composition, Notation, Analysis",
#   "canonical_alias": "#musictheory:matrix.org",
#   "joined_members": 127,
#   "joined_local_members": 2,
#   "joined_local_devices": 2,
#   "version": "1",
#   "creator": "@foo:matrix.org",
#   "encryption": null,
#   "federatable": true,
#   "public": true,
#   "join_rules": "invite",
#   "guest_access": null,
#   "history_visibility": "shared",
#   "state_events": 93534,
#   "room_type": "m.space",
#   "forgotten": false
# }

# GET /_synapse/admin/v1/rooms/<room_id> -- details contains avatar. List does not have it.
# GET /_synapse/admin/v1/rooms
# https://github.com/element-hq/synapse/blob/develop/docs/admin_api/rooms.md




# print("in group")
# _group = Group("!admin:chat.b1.shuwantech.com")
# _group.group_settings_update(avatar_http_url = "http://test")
# print(_group.settings)

async def create_group(self, group_alias, group_topic):
    # The Matrix API endpoint to check if a room exists
    check_url = f"{self.homeserver_URL}/_matrix/client/r0/directory/room/{group_alias}"
    
    headers = {
        "Authorization": f"Bearer {self.as_token}",
        "Content-Type": "application/json"
    }
    
    if "#" in group_alias:
        group_name = group_alias.split(":")[0][1:]
    else:
        group_name = group_alias
    
    # Check if the group already exists
    check_response = requests.get(check_url, headers=headers)
    if check_response.status_code == 200:
        logger.info(f"Group with alias '{group_alias}' already exists.")
        return {"status": "exists", "message": f"Group with alias '{group_alias}' already exists."}
    
    elif check_response.status_code != 404:
        logger.error(f"Error checking group existence: {check_response.status_code} - {check_response.text}")
        return {"status": "error", "message": f"Error checking group: {check_response.status_code}"}
    
    # The Matrix API endpoint to create a room (group)
    url = f"{self.homeserver_URL}/_matrix/client/r0/createRoom"
        
    # Room creation payload
    data = {
        "preset": "public_chat",  # You can use different presets like private_chat
        "name": group_name,
        "topic": group_topic,
        "visibility": "public",  # "private" or "restricted"
        "invite": [],  # You can pre-invite some users here
    }
    
    # Send request to create the room
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        logger.info(f"Group '{group_name}' created successfully.")
        return {"status": "created", "message": f"Group '{group_name}' created successfully."}
    else:
        logger.error(f"Error creating group: {response.status_code} - {response.text}")
        return {"status": "error", "message": f"Error creating group: {response.status_code}"}

async def join_group(self, group_id=None, group_alias=None, agent_ids=[]):
    if not group_id and not group_alias:
        logger.error("Error: No group ID or alias provided.")
        return
    
    # If room_alias is provided, resolve it to room_id
    if group_alias:
        logger.info(f"Resolving room alias: {group_alias} to room ID.")
        # Matrix API to resolve room alias to room ID
        resolve_url = f"{self.homeserver_URL}/_matrix/client/r0/directory/room/{group_alias}"
        headers = {
            "Authorization": f"Bearer {self.as_token}",
            "Content-Type": "application/json"
        }
        
        # Send request to resolve alias
        resolve_response = requests.get(resolve_url, headers=headers)
        if resolve_response.status_code == 200:
            group_id = resolve_response.json().get("room_id")
            logger.info(f"Resolved room alias {group_alias} to room ID: {group_id}")
        else:
            logger.error(f"Error resolving room alias {group_alias}: {resolve_response.status_code} - {resolve_response.text}")
            return
    
    # Proceed with joining the group using room_id (resolved or provided)
    if not group_id:
        logger.error("Error: No valid room ID to join.")
        return
    
    logger.info(f"Joining agents to room with ID: {group_id}.")

    # Join each agent to the room
    for agent_id in agent_ids:
        logger.info(f"Agent {agent_id} joining group with room ID {group_id}.")

        # Retrieve the bot's AsyncClient from self.clients using the agent ID
        client = self.clients.get(agent_id)
        if client:
            bot_token = client.access_token  # Access token for the bot
        else:
            logger.error(f"Bot client for {agent_id} not found.")
            continue
        
        # Matrix API to join a room (group)
        url = f"{self.homeserver_URL}/_matrix/client/r0/join/{group_id}"
        headers = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json"
        }

        # Send request for the agent to join the room
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            logger.info(f"Agent {agent_id} successfully joined group with room ID {group_id}.")
        else:
            logger.error(f"Error joining group for agent {agent_id}: {response.status_code} - {response.text}")

