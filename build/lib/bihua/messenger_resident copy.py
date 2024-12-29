from pydantic import BaseModel, Field
import os, json, requests
from typing import List, Optional,Tuple, Dict, Any, Union
from bihua_one_star import Star
from bihua_logging import get_logger
import utilities
from nio import AsyncClient, RoomMemberEvent, RoomMessageText, MatrixRoom,RoomMessageVideo, RoomMessageAudio, RoomMessageImage, RoomMessageFile
from status_definitions import CrudStatus

logger = get_logger()

class ResidentSettings(BaseModel):
    resident_id: str = None
    password: str = None
    access_token: str = None
    homeserver_url: str = None

    username: str = None
    display_name: str = None
    avatar_http_url: str = None
    email: str = None

    agent: str = None  # agent or human
    role: str = None  # admin or not
    state: str = None  # active or not

    last_login_timestamp_ms: float = 0
    last_sync_timestamp_ms: float = 0

    profile_text_path: str = None
    profile_json_path: str = None


# when we register user, Resident settings has been created. If not then we are registerting user
class Resident():
    resident_id: str
    messenger_client: AsyncClient = None
    resident_star: Star = None
    settings: ResidentSettings = None

    # Initialize with resident_id and reference StarSettings
    def __init__(self, resident_id: str):
        self.resident_id = resident_id
        self.resident_star = Star()
        self.messenger_client = AsyncClient(self.resident_star.messenger_server_url, resident_id)
        self.settings = resident_settings_load(resident_id)
        if self.settings is not None:
            return
        
        username, servername = utilities.split_resident_id(resident_id)
        profile_text_path = os.path.join(self.resident_star.star_residents_data_home, resident_id, self.resident_star.resident_profile_subfolder, f"{resident_id}.txt")
        profile_json_path = os.path.join(self.resident_star.star_residents_data_home, resident_id, self.resident_star.resident_profile_subfolder, f"{resident_id}.json")
        # new settings, create data and save them
        self.settings = resident_settings_create(
            resident_id=resident_id,
            password="thisismy.password",
            access_token="",
            homeserver_url=self.resident_star.messenger_server_url,
            username=username,
            display_name=username,
            avatar_http_url="",
            email="",
            agent="agent",
            role="admin",
            state="active",
            last_login_timestamp_ms=0,
            last_sync_timestamp_ms=0,
            profile_text_path=profile_text_path,
            profile_json_path=profile_json_path
        )
        profile_text = "Please enter agent profile text here..."
        self.resident_profile_create_or_update(profile_text=profile_text)
        logger.info(f"{resident_id} is initialized.")

    def resident_settings_update(self, **updates):
        """
        Updates the attributes of the ResidentSettings instance.
        The `**updates` argument allows for passing dynamic key-value pairs.
        """
        # Load existing resident_settings
        self.settings = resident_settings_load(self.resident_id)
        if not self.settings:
            print(f"Resident resident_settings for {self.resident_id} could not be loaded.")
            return

        # Apply updates
        for field, value in updates.items():
            if hasattr(self.settings, field):
                setattr(self.settings, field, value)
            else:
                print(f"Warning: {field} is not a valid attribute of ResidentSettings.")
        
        # After updating the attributes, save the resident_settings
        resident_settings_save(self.settings)
        print(f"Updated resident_settings for {self.resident_id} and saved.")

    def resident_profile_create_or_update(self, profile_text: str) -> CrudStatus:
        """
        Saves the resident profile text to the specified file path. 
        Returns a CrudStatus indicating the operation's result.
        """
        try:
            with open(self.settings.profile_text_path, 'w') as file:
                file.write(profile_text)
                logger.info(f"Resident profile successfully saved to {self.settings.profile_text_path}.")
                return CrudStatus.SUCCESS
        except Exception as e:
            logger.exception(f"Failed to save resident profile to {self.settings.profile_text_path}: {e}")
            return CrudStatus.EXCEPTION


    def resident_profile_load(self) -> Tuple[CrudStatus, Optional[str]]:
        """
        Loads the resident profile text from the specified file path.
        Returns a tuple containing a CrudStatus and the profile text (or None if an error occurs).
        """
        try:
            with open(self.settings.profile_text_path, 'r') as file:
                profile_text = file.read()
                logger.info(f"Resident profile successfully loaded from {self.settings.profile_text_path}.")
                return CrudStatus.SUCCESS, profile_text
        except FileNotFoundError:
            logger.warning(f"Resident profile file not found at {self.settings.profile_text_path}. Returning an empty profile.")
            return CrudStatus.ERROR, None
        except Exception as e:
            logger.exception(f"Failed to load resident profile from {self.settings.profile_text_path}: {e}")
            return CrudStatus.EXCEPTION, None



    async def on_text_message(self, room: MatrixRoom, event:RoomMessageText):
        pass

    async def on_image_message(room:MatrixRoom, event:RoomMessageImage):
        pass

    async def on_audio_message(room: MatrixRoom, event: RoomMessageAudio):
        pass

    async def on_file_message(room: MatrixRoom, event: RoomMessageFile):
        pass

    async def on_video_message(roon:MatrixRoom, event: RoomMessageVideo):
        pass

    async def on_room_member_event(event: RoomMemberEvent):
        pass
  
    ##########################################
    #
    # Add messging part to the class
    #
    ##########################################

def resident_settings_create(
    resident_id: str,
    password: str = None,
    access_token: str = None,
    homeserver_url: str = None,
    username: str = None,
    display_name: str = None,
    avatar_http_url: str = None,
    email: str = None,
    agent: str = None,
    role: str = None,
    state: str = None,
    last_login_timestamp_ms: float = 0,
    last_sync_timestamp_ms: float = 0,
    profile_text_path: str = None,
    profile_json_path: str = None
) -> ResidentSettings:
    # Create the ResidentSettings instance
    resident_settings = ResidentSettings(
        resident_id=resident_id,
        password=password,
        access_token=access_token,
        homeserver_url=homeserver_url,
        username=username,
        display_name=display_name,
        avatar_http_url=avatar_http_url,
        email=email,
        agent=agent,
        role=role,
        state=state,
        last_login_timestamp_ms=last_login_timestamp_ms,
        last_sync_timestamp_ms=last_sync_timestamp_ms,
        profile_text_path=profile_text_path,
        profile_json_path=profile_json_path
    )

    try:
        _star = Star()
        # Define the file path for saving the resident_settings
        setting_json_file_location = os.path.join(_star.star_residents_data_home, resident_id, _star.resident_profile_subfolder)
        setting_json_file = os.path.join(setting_json_file_location, f"{resident_id}.json")
        
        # Create the necessary directory if it doesn't exist
        if not os.path.exists(setting_json_file_location):
            os.makedirs(setting_json_file_location)

        # Save the resident_settings to the JSON file using to_dict()
        with open(setting_json_file, 'w') as f:
            f.write(resident_settings.model_dump_json())
        # print(f"Settings for {resident_settings.resident_id} saved successfully.")
        return resident_settings
    except Exception as e:
        print(f"Error saving resident_settings for {resident_settings.resident_id}: {e}")

# dump setting content to json file
def resident_settings_save(resident_settings:ResidentSettings) -> CrudStatus:
    if resident_settings is None:
        return CrudStatus.ERROR
    try:
        _star = Star()
        # Define the file path for saving the resident_settings
        setting_json_file_location = os.path.join(_star.star_residents_data_home, resident_settings.resident_id, _star.resident_profile_subfolder)
        setting_json_file = os.path.join(setting_json_file_location, f"{resident_settings.resident_id}.json")
        
        # Create the necessary directory if it doesn't exist
        if not os.path.exists(setting_json_file_location):
            os.makedirs(setting_json_file_location)

        # Save the resident_settings to the JSON file using to_dict()
        with open(setting_json_file, 'w') as f:
            f.write(resident_settings.model_dump_json())
        print(f"Settings for {resident_settings.resident_id} saved successfully.")
    except Exception as e:
        print(f"Error saving resident_settings for {resident_settings.resident_id}: {e}")

# if not loaded properly, return None
def resident_settings_load(resident_id:str) -> ResidentSettings:
    try:
        # print("Loading resident resident_settings...")
        logger.info(f"Loading resident settings for {resident_id}")
        _star = Star()
        setting_json_file_location = os.path.join(_star.star_residents_data_home, resident_id, _star.resident_profile_subfolder)
        setting_json_file = os.path.join(setting_json_file_location, f"{resident_id}.json")

        # setting_json_file = f"{setting_json_file_location}/{resident_id}.json"
        # print(f"Looking for resident_settings file at {setting_json_file}")

        # Load resident_settings if the file exists
        if os.path.exists(setting_json_file):
            with open(setting_json_file, 'r') as f:
                setting_json = json.load(f)
                if not setting_json:  # Check if the loaded JSON is empty
                    return None
            _settings = ResidentSettings(**setting_json)
            logger.info(f"{resident_id}'s data is loaded.")
            return _settings
        else:
            logger.info(f"{resident_id}'s data has not been initialized yet...")
            return None

    except Exception as e:
        logger.error(f"Error loading resident_settings for {resident_id}: {e}")
        return None

def resident_settings_update(resident_id:str, **updates):
        """
        Updates the attributes of the ResidentSettings instance.
        The `**updates` argument allows for passing dynamic key-value pairs.
        """
        # Load existing resident_settings
        settings = resident_settings_load(resident_id)
        if not settings:
            print(f"Resident resident_settings for {resident_id} could not be loaded.")
            return

        # Apply updates
        for field, value in updates.items():
            if hasattr(settings, field):
                setattr(settings, field, value)
            else:
                print(f"Warning: {field} is not a valid attribute of ResidentSettings.")
        
        # After updating the attributes, save the resident_settings
        resident_settings_save(settings)
        print(f"Updated resident_settings for {resident_id} and saved.")

# # Assuming you have already defined your ResidentSettings class and helper functions

# # Example: Update the resident_settings for resident_123
# resident_id = "resident_123"

# # Update fields using the `update` function
# update(
#     resident_id,
#     display_name="New Display Name",         # Update the display name
#     email="new.email@example.com",           # Update the email
#     last_login_timestamp_ms=1623470400000   # Update the last login timestamp
# )

# # After calling this, the updated resident_settings will be saved automatically
# print("in resident")
# _resident = Resident("@admin:chat.b1.shuwantech.com")
# _resident.resident_settings_update(password = "test")
# print(_resident.settings)

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

# GET /_synapse/admin/v2/users/<user_id>
# GET /_synapse/admin/v2/users?from=0&limit=10&guests=false
# https://github.com/element-hq/synapse/blob/develop/docs/admin_api/user_admin_api.md

def get_all_residents_from_messenger(base_url: str, access_token: str, limit: int = 10) -> List[dict]:
    """
    Fetches all users from the Synapse server using the admin API.

    Args:
    - base_url (str): The base URL of the Synapse server.
    - access_token (str): The access token for authenticating the request.
    - limit (int): Number of users to fetch per request (default is 10).

    Returns:
    - List[dict]: List of all users retrieved from the API.
    """
    url = f"{base_url}/_synapse/admin/v2/users"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"from": 0, "limit": limit, "guests": "false"}
    all_users = []

    try:
        while True:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code >= 200 and response.status_code < 300:
                data = response.json()
                users = data.get("users", [])
                if not users:
                    break
                all_users.extend(users)
                params["from"] += limit
            else:
                logger.error(f"Failed to retrieve users. Status code: {response.status_code}, Response: {response.text}")
                break
    except requests.RequestException as e:
        logger.exception("Error while making request to Synapse server.")
    except Exception as e:
        logger.exception("An unexpected error occurred while fetching users.")
    return all_users

def map_and_save_residents_settings(_residents_json_list: List[dict]) -> CrudStatus:
    """
    Maps resident data and saves the settings.

    Args:
    - _residents_json_list (List[dict]): List of resident data from the API.

    Returns:
    - CrudStatus: The status of the operation.
    """
    try:
        for _resident_json in _residents_json_list:
            try:
                username, servername = utilities.split_resident_id(_resident_json.get("name"))
                avatar_url = (
                    utilities.convert_mxc_to_url(_resident_json.get("avatar_url"))
                    if _resident_json.get("avatar_url")
                    else ""
                )
                _resident = Resident(_resident_json.get("name"))
                _resident.resident_settings_update(
                # _resident_settings = ResidentSettings(
                    resident_id=_resident_json.get("name"),
                    username=username,
                    display_name=_resident_json.get("displayname"),
                    avatar_http_url=avatar_url,
                    role="admin" if _resident_json.get("admin") else "user",
                    state="active" if not _resident_json.get("deactivated") else "inactive",
                    last_login_timestamp_ms=_resident_json.get("last_seen_ts", 0),
                    last_sync_timestamp_ms=0
                )
                # _resident.settings = _resident_settings
                resident_settings_save(_resident.settings)
                logger.info(f"Successfully saved settings for resident: {_resident_json.get('name')}")
            except KeyError as e:
                logger.warning(f"Missing key in resident data: {e}, Data: {_resident_json}")
            except Exception as e:
                logger.exception(f"Error processing resident data: {_resident_json}")
    except Exception as e:
        logger.exception("An unexpected error occurred while mapping and saving residents settings.")

def collect_and_save_residents_settings() -> CrudStatus:
    """
    Collects and saves resident settings.

    Returns:
    - CrudStatus: The status of the operation.
    """
    try:
        _star = Star()
        resident_data_collected = get_all_residents_from_messenger(
            _star.messenger_server_url, _star.messenger_admin_access_token
        )
        map_and_save_residents_settings(resident_data_collected)
        logger.info("Successfully collected and saved resident settings.")
        return CrudStatus.SUCCESS
    except Exception as e:
        logger.exception("An unexpected error occurred in collect_and_save_residents_settings.")
        return CrudStatus.EXCEPTION

# {
#     'name': '@admin:messenger.b1.shuwantech.com',
#     'admin': True,
#     'deactivated': False,
#     'locked': False,
#     'shadow_banned': False,
#     'creation_ts': 1731660775,
#     'appservice_id': None,
#     'consent_server_notice_sent': None,
#     'consent_version': None,
#     'consent_ts': None,
#     'user_type': None,
#     'is_guest': False,
#     'displayname': 'admin',
#     'avatar_url': None,
#     'threepids': [],
#     'external_ids': [],
#     'erased': False,
#     'last_seen_ts': 1732704887848
# }

def get_resident_data_from_messenger(resident_id: str) -> Tuple[str, Union[dict, None]]:
    try:
        _star = Star()
        url = f"{_star.messenger_server_url}/_synapse/admin/v2/users/{resident_id}"
        headers = {"Authorization": f"Bearer {_star.messenger_admin_access_token}"}
        response = requests.get(url, headers=headers)

        if 200 <= response.status_code < 300:
            logger.info(f"Successfully retrieved data for resident ID: {resident_id}")
            return CrudStatus.SUCCESS, response.json()
        else:
            logger.error(
                f"Failed to retrieve data for resident ID: {resident_id}. HTTP Status: {response.status_code}, Response: {response.text}"
            )
            return CrudStatus.ERROR, None
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred while retrieving data for resident ID: {resident_id}."
        )
        return CrudStatus.EXCEPTION, None



def sync_resident(resident:Resident):
    data_status, resident_json = get_resident_data_from_messenger(resident.settings.resident_id)
    if data_status != CrudStatus.SUCCESS: # user does not exists
        pass

    # check if resident folder exists
    if os.path.isfile(resident.settings.profile_json_path): # file exists

        pass
    



    #if it exists in the residents folder


    


    # sync fields

# get_resident_data_from_messenger("@admin:messenger.b1.shuwantech.com")

def update_resident_settings(resident_settings: ResidentSettings, json_data: dict):
    mapping = {
        "username": "name",
        "display_name": "displayname",
        "avatar_http_url": "avatar_url",
        "last_login_timestamp_ms": "last_seen_ts",
    }

    updated_fields = []
    for field, json_key in mapping.items():
        json_value = json_data.get(json_key)
        if getattr(resident_settings, field) != json_value:
            setattr(resident_settings, field, json_value)
            updated_fields.append(field)

    # Example for additional fields
    if json_data.get("admin") is not None:
        role = "admin" if json_data["admin"] else "user"
        if resident_settings.role != role:
            resident_settings.role = role
            updated_fields.append("role")

    if json_data.get("deactivated") is not None:
        state = "inactive" if json_data["deactivated"] else "active"
        if resident_settings.state != state:
            resident_settings.state = state
            updated_fields.append("state")

    return updated_fields