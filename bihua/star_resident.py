from pydantic import BaseModel, Field
import os, json, requests, mimetypes, aiofiles
from typing import List, Optional,Tuple, Any, Union
from bihua_star import Star
from bihua_logging import get_logger
import utilities
from nio import AsyncClient, UploadResponse
from status_definitions import CrudStatus, RegisterStatus, LoginStatus, CheckCrudStatus

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

    last_login_timestamp_ms: float = 0.0
    last_sync_timestamp_ms: float = 0.0

    profile_text_path: str = None
    profile_json_path: str = None


# When resident is not registered, creating this object will return None
# If resident is registered, this will
# 1) get data from register
# 2) create or sync with local profile json, create profile text if not created but will not touch text.
class Resident():
    resident_id: str
    messenger_client: AsyncClient = None
    resident_star: Star = None
    settings: ResidentSettings = None

    # Initialize with resident_id and reference StarSettings
    def __init__(self, resident_id: str):
        try:
            settings_status, settings = create_update_resident_settings(resident_id)
            if settings_status != CrudStatus.SUCCESS:
                logger.error(f"Resident initialization failed for resident_id={self.resident_id}.")
                return None
            
            _star = Star()
            self.resident_id = resident_id
            self.messenger_client = AsyncClient(_star.messenger_server_url, resident_id)
            self.settings = settings # created and loaded 
            self.resident_star = _star
            logger.info(f"Resident successfully initialized for resident_id={self.resident_id}.")
        except Exception as e:
            logger.exception(f"Resident initialization failed for resident_id={self.resident_id}.")

    # Update and sync with messenger server. Then load new data.
    def resident_settings_update(self, **updates):
        print(f"HELLO------resident_settings_update {updates}")
        try:
            update_status, settings = resident_settings_update_sync_save(self.resident_id, **updates)
            print(f"HELLO------update result {update_status}   {settings}")
            if update_status == CrudStatus.SUCCESS:
                self.settings = settings
                logger.info(f"Resident settings updated successfully for resident_id={self.resident_id}.")
            else:
                logger.exception(f"Failed to update resident settings for resident_id={self.resident_id}. Updates attempted: {updates}")
        except Exception as e:
            logger.exception(f"Failed to update resident settings for resident_id={self.resident_id}. Updates attempted: {updates}")

    # This will save the text to profile txt file
    def resident_text_profile_create_or_update(self, profile_text: str) -> CrudStatus:
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

    # This will load the text from profile txt file
    def resident_text_profile_load(self) -> Tuple[CrudStatus, Optional[str]]:
        """
        Loads the resident profile text from the specified file path.
        Returns a tuple containing a CrudStatus and the profile text (or None if an error occurs).
        """
        try:
            with open(self.settings.profile_text_path, 'r') as file:
                profile_text = file.read()
                logger.info(f"Resident profile successfully loaded from {self.settings.profile_text_path}.")
                return CrudStatus.SUCCESS, profile_text
        except Exception as e:
            logger.exception(f"Failed to load resident profile from {self.settings.profile_text_path}: {e}")
            return CrudStatus.EXCEPTION, None


# PUBLIC FUNCTION
# To be used for loading text profile without creating Resident class. lighter.
def resident_text_profile_load(resident_id: str):
    try:
        load_status, settings = resident_settings_load(resident_id)
        if load_status == CrudStatus.SUCCESS:
            with open(settings.profile_text_path, 'r') as file:
                profile_text = file.read()
                logger.info(f"Resident profile successfully loaded from {settings.profile_text_path}.")
                return CrudStatus.SUCCESS, profile_text
    except Exception as e:
        logger.exception(f"Failed to load resident profile from {settings.profile_text_path}: {e}")
        return CrudStatus.EXCEPTION, None

# PUBLIC FUNCTION
# To be used for create and update text profile without creating Resident class. lighter.
def resident_text_profile_create_or_update(resident_id:str, profile_text:str):
    try:
        load_status, settings = resident_settings_load(resident_id)
        if load_status == CrudStatus.SUCCESS:
            with open(settings.profile_text_path, 'w') as file:
                file.write(profile_text)
                logger.info(f"Resident profile successfully saved to {settings.profile_text_path}.")
                return CrudStatus.SUCCESS
        else:
            logger.error(f"Failed to save resident profile to {settings.profile_text_path}")
            return CrudStatus.ERROR
    except Exception as e:
        logger.exception(f"Failed to save resident profile to {settings.profile_text_path}: {e}")
        return CrudStatus.EXCEPTION

# PRIVATE FUNCTION
# Do one resident
# Called by other functions in this module.
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

# PRIVATE FUNCTION
# Do one resident
# Called by other functions in this module.
# if not loaded properly, return None
def resident_settings_load(resident_id: str) -> Tuple[CrudStatus, Optional['ResidentSettings']]:
    try:
        logger.info(f"Loading resident settings for {resident_id}")
        _star = Star()  # Assuming this initializes properly
        setting_json_file_location = os.path.join(
            _star.star_residents_data_home, resident_id, _star.resident_profile_subfolder
        )
        setting_json_file = os.path.join(setting_json_file_location, f"{resident_id}.json")

        if os.path.exists(setting_json_file):
            with open(setting_json_file, 'r') as f:
                setting_json = json.load(f)
                if not setting_json:  # Check if the loaded JSON is empty
                    logger.info(f"{resident_id}'s settings file is empty.")
                    return CrudStatus.SUCCESS, None # when empty json
            _settings = ResidentSettings(**setting_json)  # Assuming ResidentSettings initialization
            logger.info(f"{resident_id}'s data is successfully loaded.")
            return CrudStatus.SUCCESS, _settings
        else:
            logger.info(f"{resident_id}'s data has not been initialized yet...")
            return CrudStatus.ERROR, None

    except Exception as e:
        logger.error(f"Error loading resident_settings for {resident_id}: {e}")
        return CrudStatus.EXCEPTION, None

# PRIVATE FUNCTION
# Do one resident
# It is called by create_update_resident_settings()
# Return data if resident exists, None if not.
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


# PUBLIC FUNCTION
# Do one resident
# Assume resident is registered. if not registered, call register function before calling this.
# This function will get data from messenger server, create or update settings (profile txt and profile json)
def create_update_resident_settings(resident_id: str) -> Tuple[CrudStatus, ResidentSettings]:
    # get data from messenger server
    create_status, resident_settings_json = get_resident_data_from_messenger(resident_id=resident_id)

    if create_status != CrudStatus.SUCCESS:
        logger.error(f"Failed to retrieve data of resident {resident_id} from messenger server.")
        return CrudStatus.ERROR, None
    
    # prepare local profile json and txt
    _star = Star()
    try:
        # prepare profile text
        profile_text_path = os.path.join(_star.star_residents_data_home, resident_id, _star.resident_profile_subfolder, f"{resident_id}.txt")
        profile_json_path = os.path.join(_star.star_residents_data_home, resident_id, _star.resident_profile_subfolder, f"{resident_id}.json")

        os.makedirs(os.path.dirname(profile_text_path), exist_ok=True) # both txt and json are in the same directory, check once
        if not os.path.exists(profile_text_path):
            profile_text = "Please enter agent profile text here..."
            with open(profile_text_path, 'w') as file:
                file.write(profile_text)  # Create an empty file
        
        # prepare profile json
        load_status, resident_settings = resident_settings_load(resident_id)
        if load_status != CrudStatus.SUCCESS or (load_status == CrudStatus.SUCCESS and resident_settings is None):
            print(f"Creating settings for {resident_id}    {resident_settings_json}")
            resident_settings = ResidentSettings()
            resident_settings.resident_id = resident_id
            resident_settings.password = "thisismy.password"
            resident_settings.access_token = ""
            resident_settings.homeserver_url = _star.messenger_server_url
            resident_settings.username = resident_settings_json.get("displayname")

            print(f"resident_settings.username {resident_settings.username}")

            resident_settings.display_name = resident_settings_json.get("displayname")
            if resident_settings_json["avatar_url"] is None:
                resident_settings.avatar_http_url = ""
            else:
                resident_settings.avatar_http_url = utilities.convert_mxc_to_url(resident_settings_json["avatar_url"], _star.messenger_server_url)
            resident_settings.email = ""
            resident_settings.agent = "agent"
            resident_settings.role = "admin" if resident_settings_json.get("admin") else "user"
            resident_settings.state = "active" if not resident_settings_json.get("deactivated") else "inactive"

            v = resident_settings_json.get("last_seen_ts", 0)
            print(f"CREATE: resident_settings.state {v}")

            resident_settings.last_login_timestamp_ms = resident_settings_json.get("last_seen_ts", 0)
            print(f"CREATE: resident_settings.last_login_timestamp_ms {resident_settings.last_login_timestamp_ms}")

            resident_settings.last_sync_timestamp_ms = 0
            resident_settings.profile_text_path = profile_text_path
            resident_settings.profile_json_path = profile_json_path

            print(f"Saving settings for {resident_id}")
            resident_settings_save(resident_settings)
            print(f"Appending resident json list for {resident_id}")
            append_resident_json_list(resident_id=resident_id)
            logger.info(f"Created and saved settings for {resident_id}")
        else:
            print(f"Updating settings for {resident_id}")
            resident_settings.resident_id
            # resident_settings.resident_id = resident_id
            # resident_settings.password = "thisismy.password"
            # resident_settings.access_token = ""
            # resident_settings.homeserver_url = _star.messenger_server_url
            # resident_settings.username = resident_settings_json.get("displayname")
            resident_settings.display_name = resident_settings_json.get("displayname")
            if resident_settings_json["avatar_url"] is None:
                resident_settings.avatar_http_url = ""
            else:
                resident_settings.avatar_http_url = utilities.convert_mxc_to_url(resident_settings_json["avatar_url"], _star.messenger_server_url)
            # resident_settings.email = ""
            # resident_settings.agent = "agent"
            resident_settings.role = "admin" if resident_settings_json.get("admin") else "user"
            resident_settings.state = "active" if not resident_settings_json.get("deactivated") else "inactive"
            v = resident_settings_json.get("last_seen_ts", 0)
            print(f"UPDATE: resident_settings.state {v}")

            resident_settings.last_login_timestamp_ms = resident_settings_json.get("last_seen_ts", 0)
            print(f"UPDATE ONE: resident_settings.last_login_timestamp_ms {resident_settings.last_login_timestamp_ms}")

            # resident_settings.last_sync_timestamp_ms = 0
            # resident_settings.profile_text_path = profile_text_path
            # resident_settings.profile_json_path = profile_json_path

            resident_settings_save(resident_settings)
            update_resident_json_list(resident_id=resident_id)
            logger.info(f"Updated and saved settings for {resident_id}")
            
        return CrudStatus.SUCCESS, resident_settings

    except Exception as e:
        logger.exception(f"An exception occurred while creating or updating settings for {resident_id}: {e}")
        return CrudStatus.EXCEPTION, None

# PUBLIC FUNCTIOM: registration will just register to messenger server, settings will be saved, text profile file will be created.
# Register one resident.
# This uses Star class, does not use Resident class.
# It does not return anything, things will be in Messenger server, profile txt and json in data directory.
async def register_user(username: str, password: str, homeserver_url: str) -> RegisterStatus:
    if not utilities.is_valid_username(username):
        logger.error(f"Invalid username provided: {username}")
        return RegisterStatus.INVALID_USERNAME
    try:
        resident_id_to_register = f"@{username}:{utilities.extract_homeserver_name(homeserver_url)}"
        _star = Star()

        url = f"{_star.messenger_server_url}/_synapse/admin/v2/users/{resident_id_to_register}"

        headers = {
            "Authorization": f"Bearer {_star.messenger_admin_access_token}"
        }

        # Check if the user already exists
        logger.debug(f"Checking if user {resident_id_to_register} already exists.")
        response = requests.get(url, headers=headers)
        if 200 <= response.status_code < 300:
            logger.info(f"User {resident_id_to_register} already exists.")
            return RegisterStatus.USER_EXISTS

        # Proceed to create the user if it doesn't exist
        data = {
            "password": password,
            "display_name": username,
            "admin": True,
            "deactivated": False,
        }

        logger.debug(f"Creating user {resident_id_to_register}.")
        response = requests.put(url, json=data, headers=headers)

        if 200 <= response.status_code < 300:
            logger.info(f"User {resident_id_to_register} created successfully.")

            # Fetch the user data and create/update resident settings: both profile txt and profile json
            logger.debug(f"Updating resident settings for {resident_id_to_register}.")
            result_status, resident_settings = create_update_resident_settings(resident_id_to_register)
            if result_status != CrudStatus.SUCCESS:
                logger.error(f"Failed to create/update resident settings for {resident_id_to_register}.")
                return RegisterStatus.ERROR

            _client = AsyncClient(_star.messenger_server_url, resident_id_to_register)
            await _client.login(password)
            access_token = _client.access_token
            await _client.logout()
            await _client.close()

            resident_settings.access_token = access_token
            resident_settings_save(resident_settings)  # Finish updating access_token
            logger.info(f"Access token updated for user {resident_id_to_register}.")
            append_resident_json_list(resident_id_to_register)
            return RegisterStatus.SUCCESS
        else:
            logger.error(f"Failed to create user {resident_id_to_register}. HTTP status: {response.status_code}, Response: {response.text}")
            return RegisterStatus.ERROR
    except Exception as e:
        logger.exception(f"An exception occurred while registering user {username}: {e}")
        return RegisterStatus.EXCEPTION


# PRIVATE and PUBLIC FUNCTION
# Called by other functions in this module.
# It update, sync with messenger server, return the settings
def resident_settings_update_sync_save(resident_id:str, **updates) -> Tuple[CrudStatus, ResidentSettings]:
        """
        Updates the attributes of the ResidentSettings instance.
        The `**updates` argument allows for passing dynamic key-value pairs.
        """
        try:
            # Load existing resident_settings
            load_status, settings = resident_settings_load(resident_id)
            if load_status != CrudStatus.SUCCESS:
                logger.info(f"Resident resident_settings for {resident_id} could not be loaded.")
                _status, settings = create_update_resident_settings(resident_id)
                if _status != CrudStatus.SUCCESS:
                    return CrudStatus.EXCEPTION, None
                else:
                    logger.info(f"Resident resident_settings for {resident_id} created.")
            else:
                logger.info(f"Resident resident_settings for {resident_id} is loaded.")
            # Apply updates
            print(f"HELLO................")
            for field, value in updates.items():
                if hasattr(settings, field):
                    setattr(settings, field, value)
                else:
                    logger.error(f"{field} is not a valid attribute of ResidentSettings.")
            
            # After updating the attributes, save the resident_settings
            resident_settings_save(settings)
            print(f"BYE 1................")
            # sync data from resident
            create_update_resident_settings(resident_id)
            print(f"BYE 2................")
            return CrudStatus.SUCCESS, settings
        except Exception as e:
            logger.exception(f"Exception occurred in residetn setting update: {e}")
            return CrudStatus.EXCEPTION, None


# PRIVATE FUNCTION
# Called by collect_and_save_residents_settings()
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

# PRIVATE FUNCTION
# Called by collect_and_save_residents_settings()
def map_and_save_all_resident_settings(_residents_json_list: List[dict]) -> CrudStatus:

    try:
        for _resident_json in _residents_json_list:
            resident_settings_update_sync_save(_resident_json.get("name"), _resident_json)
        logger.info(f"Successfully saved settings for resident settings list.")
    except Exception as e:
        logger.exception("An unexpected error occurred while mapping and saving residents settings.") 


# PULIC FUNCTION
# This function will synch each resident json profile based on its data in messenger
def sync_and_save_all_resident_settings() -> CrudStatus:
    """
    Collects and saves resident settings.

    Returns:
    - CrudStatus: The status of the operation.
    """
    try:
        _star = Star()
        _residents_json_list = get_all_residents_from_messenger(
            _star.messenger_server_url, _star.messenger_admin_access_token
        )
        map_and_save_all_resident_settings(_residents_json_list)
        logger.info("Successfully collected and saved resident settings.")
        return CrudStatus.SUCCESS
    except Exception as e:
        logger.exception("An unexpected error occurred in collect_and_save_residents_settings.")
        return CrudStatus.EXCEPTION
    

# def generate_resident_json_list():
#     try:
#         _star = Star()
#         resident_list = []
#         # Iterate over resident directories
#         for resident_id in os.listdir(_star.star_residents_data_home):
#             resident_profile_full_path = os.path.join(_star.star_residents_data_home, resident_id, _star.resident_profile_subfolder)
#             json_file_path = os.path.join(resident_profile_full_path, f"{resident_id}.json")
#             if os.path.exists(json_file_path):
#                 with open(os.path.join(resident_profile_full_path, f"{resident_id}.json"), 'r') as f:
#                     resident_json = json.load(f)
#                     resident_list.append(resident_json)

#             if len(resident_list) > 0:
#                 with open(_star.resident_list_json_path, 'w') as f:
#                     json.dump(resident_list, f, indent=4)
#             else:
#                 with open(_star.resident_list_json_path, 'w') as file:
#                     file.write("{}")  # Create an empty JSON file

#         logger.info(f"Resident list successfully saved to {_star.resident_list_json_path}.")

#     except Exception as e:
#         logger.exception("Unexpected error in generate_resident_json_list.")



# Append the resident data to the list, so resident list will be up to date.
def append_resident_json_list(resident_id) -> CrudStatus:
    try:
        _star = Star()

        path_of_resident_profile_json_to_append = os.path.join(_star.star_residents_data_home, resident_id, _star.resident_profile_subfolder, f"{resident_id}.json")
        logger.debug(f"Loading resident profile json from {path_of_resident_profile_json_to_append}")

        with open(_star.resident_list_json_path, 'r') as f:
            resident_json_list = json.load(f)

        with open(path_of_resident_profile_json_to_append, 'r') as f:
            resident_json = json.load(f)

        resident_json_list.append(resident_json)
        # Save the updated json list.
        with open(_star.resident_list_json_path, 'w') as f:
            json.dump(resident_json_list, f, indent=4)

        logger.info(f"Successfully updated resident list for {resident_id}")

    except Exception as e:
        logger.exception(f"Unexpected error occurred while processing resident data in append_resident_json_list: {e}")
        return CrudStatus.EXCEPTION


def get_resident_list() -> tuple[CrudStatus, dict]:
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
    

# When one resident's setting has changed, we need to update its content in resident list
def update_resident_json_list(resident_id: str) -> CrudStatus:
    try:
        _star = Star()
        # star_residents_data_home, resident_profile_subfolder, resident_list_json_path = fetch_resident_data_paths_from_env()
        
        logger.debug(f"Loading resident list from {_star.resident_list_json_path}")
        with open(_star.resident_list_json_path, 'r') as f:
            resident_json_list = json.load(f)

        path_of_resident_profile_json_to_update = os.path.join(_star.star_residents_data_home, resident_id, _star.resident_profile_subfolder, f"{resident_id}.json")
        logger.debug(f"Loading resident profile json from {path_of_resident_profile_json_to_update}")
        with open(path_of_resident_profile_json_to_update, 'r') as f:
                resident_json_to_update = json.load(f)

        # Find the item and replace it with new one.
        for i, resident_json in enumerate(resident_json_list):
            if resident_json.get('resident_id') == resident_id:
                logger.info(f"Updating resident profile for ID {resident_id}")
                resident_json_list[i] = resident_json_to_update
                break
        else:
            logger.warning(f"Resident with ID {resident_id} not found in the list.")
            return CrudStatus.ERROR
        
        # Save the updated json list.
        with open(_star.resident_list_json_path, 'w') as f:
            json.dump(resident_json_list, f, indent=4)

        logger.info(f"Successfully updated resident list for {resident_id}")

    except Exception as e:
        logger.exception(f"Unexpected error occurred while processing resident data in update_resident_json_list: {e}")
        return CrudStatus.EXCEPTION


class ChangeUserPasswordRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose password is to be changed")
    new_displayname: str = Field(..., min_length=8, max_length=100, description="The new password for the resident account")
async def change_user_password(resident_id: str, new_password: str) -> CheckCrudStatus:
    try:
        load_status, _settings = resident_settings_load(resident_id)
        if load_status != CrudStatus.SUCCESS:
            return CheckCrudStatus.ERROR, None
        if new_password == _settings.password:
            logger.info(f"Password for resident {resident_id} is already up-to-date.")
            return CheckCrudStatus.NO_CHANGE  # No action needed

        _star = Star()
        # Construct the API URL
        url = f"{_star.messenger_server_url}/_synapse/admin/v2/users/{resident_id}"
        headers = {"Authorization": f"Bearer {_star.messenger_admin_access_token}"}
        data = {"password": new_password}
        response = requests.put(url, json=data, headers=headers)
        
        if 200 <= response.status_code < 300:
            _settings.password = new_password
            resident_settings_update_sync_save(resident_id, passwprd = new_password)
            logger.info(f"Password for resident {resident_id} updated successfully.")
            update_resident_json_list(resident_id=resident_id)
            return CheckCrudStatus.SUCCESS
        else:
            logger.error(f"Failed to update password for resident {resident_id}. "
                         f"API responded with status code {response.status_code}: {response.text}")
            return CheckCrudStatus.EXCEPTION, None
        
    except Exception as e:
        logger.exception(f"Failed to update password for resident {resident_id}.")
        return CheckCrudStatus.EXCEPTION, None
    

class ChangeUserDisplayNameRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose display name is to be changed")
    new_displayname: str = Field(..., min_length=1, description="The new display name for the resident")
async def change_user_display_name(resident_id: str, new_displayname: str) -> str:
    try:
        _settings = resident_settings_load(resident_id)
        if new_displayname == _settings.display_name:
            logger.info(f"Display name for resident {resident_id} is already up-to-date.")
            return CheckCrudStatus.NO_CHANGE  # No action needed

        _star = Star()
        # Construct the API URL
        url = f"{_star.messenger_server_url}/_synapse/admin/v2/users/{resident_id}"
        headers = {"Authorization": f"Bearer {_star.messenger_admin_access_token}"}
        data = {"displayname": new_displayname}
        response = requests.put(url, json=data, headers=headers)
        
        if 200 <= response.status_code < 300:
            _settings.password = new_displayname
            resident_settings_update_sync_save(resident_id, passwprd = new_displayname)
            logger.info(f"Display name for resident {resident_id} updated successfully.")
            update_resident_json_list(resident_id=resident_id)
            return CheckCrudStatus.SUCCESS
        else:
            logger.error(f"Failed to update display name for resident {resident_id}. "
                         f"API responded with status code {response.status_code}: {response.text}")
            return CheckCrudStatus.EXCEPTION, None

    except Exception as e:
        logger.exception(f"Failed to update display name for resident {resident_id}.")


class ChangeUserTypeRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose agent type is to be changed")
    new_agent_type: str = Field(..., min_length=1, description="The new agent type for the resident")
async def change_user_type(resident_id, new_agent_type: str):
    try:
        load_status, _settings = resident_settings_load(resident_id)
        if load_status != CrudStatus.SUCCESS:
            return CheckCrudStatus.ERROR, None
        if new_agent_type == _settings.agent:
            logger.info(f"Agent type for resident {resident_id} is already up-to-date.")
            return CheckCrudStatus.NO_CHANGE  # No action needed

        _settings.agent = new_agent_type
        _status = resident_settings_save(_settings)
        if _status == CheckCrudStatus.SUCCESS:
            update_resident_json_list(resident_id=resident_id)
            logger.info(f"Agent type for resident {resident_id} is updated.")
            return CheckCrudStatus.SUCCESS

    except Exception as e:
        logger.exception(f"Failed to update agent type for resident {resident_id}.")
        return CheckCrudStatus.EXCEPTION


class ChangeUserRoleRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose role is to be changed")
    new_role: str = Field(..., min_length=1, description="The new role for the resident")
async def change_user_role(resident_id: str, new_role: str):
    try:
        load_status, _settings = resident_settings_load(resident_id)
        if load_status != CrudStatus.SUCCESS:
            return CheckCrudStatus.ERROR, None
        if new_role == _settings.role:
            logger.info(f"Role for resident {resident_id} is already up-to-date.")
            return CheckCrudStatus.NO_CHANGE  # No action needed

        if new_role == "admin":
            data = {"admin": True}
        else:
            data = {"admin": False}

        _star = Star()
        # Construct the API URL
        url = f"{_star.messenger_server_url}/_synapse/admin/v2/users/{resident_id}"
        headers = {"Authorization": f"Bearer {_star.messenger_admin_access_token}"}
        response = requests.put(url, json=data, headers=headers)
        
        if 200 <= response.status_code < 300:
            _settings.role = new_role
            resident_settings_update_sync_save(resident_id, role = new_role)
            logger.info(f"Role for resident {resident_id} updated successfully.")
            update_resident_json_list(resident_id=resident_id)
            return CheckCrudStatus.SUCCESS
        else:
            logger.error(f"Failed to update role for resident {resident_id}. "
                         f"API responded with status code {response.status_code}: {response.text}")
            return CheckCrudStatus.EXCEPTION, None

    except Exception as e:
        logger.exception(f"Failed to update role for resident {resident_id}.")


class ChangeUserStateRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose state is to be changed")
    new_state: str = Field(..., min_length=1, description="The new state for the resident")
async def change_user_state(resident_id: str, new_state: str):
    try:
        load_status, _settings = resident_settings_load(resident_id)
        if load_status != CrudStatus.SUCCESS:
            return CheckCrudStatus.ERROR, None
        if new_state == _settings.state:
            logger.info(f"State for resident {resident_id} is already up-to-date.")
            return CheckCrudStatus.NO_CHANGE  # No action needed

        if new_state == "active":
            data = {"deactivated": False}
        else:
            data = {"deactivated": True}

        _star = Star()
        # Construct the API URL
        url = f"{_star.messenger_server_url}/_synapse/admin/v2/users/{resident_id}"
        headers = {"Authorization": f"Bearer {_star.messenger_admin_access_token}"}
        response = requests.put(url, json=data, headers=headers)
        
        if 200 <= response.status_code < 300:
            _settings.state = new_state
            resident_settings_update_sync_save(resident_id, state = new_state)
            logger.info(f"State for resident {resident_id} updated successfully.")
            update_resident_json_list(resident_id=resident_id)
            return CheckCrudStatus.SUCCESS
        else:
            logger.error(f"Failed to update state for resident {resident_id}. "
                         f"API responded with status code {response.status_code}: {response.text}")
            return CheckCrudStatus.EXCEPTION, None

    except Exception as e:
        logger.exception(f"Failed to update role for resident {resident_id}.")


# from client, we first upload avatar file to messenger server. Then we call this function to change
# avatar in mesenger
class UpdateUserAvatarInMessengerRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose avatar is to be updated")
    avatar_file_path: str = Field(..., min_length=1, description="The file path of the new avatar image")

async def update_user_avatar_in_messenger(resident_id: str, avatar_file_path: str):
    _star = Star()
    load_status, _settings = resident_settings_load(resident_id)
    if load_status != CrudStatus.SUCCESS:
        return CheckCrudStatus.ERROR, None
    logger.info(f"Attempting to update avatar for resident ID: {resident_id}")

    try:
        # Log in to the Messenger client
        logger.debug(f"Logging in to the Messenger client for resident {resident_id}")
        _client = AsyncClient(_star.messenger_server_url, resident_id)
        await _client.login(_settings.password)

        # Guess the MIME type of the avatar file
        content_type, _ = mimetypes.guess_type(avatar_file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
            logger.warning(f"Could not determine MIME type for {avatar_file_path}. Defaulting to 'application/octet-stream'.")

        # Get the file size of the avatar
        filesize = os.path.getsize(avatar_file_path)
        logger.debug(f"Avatar file size for {avatar_file_path}: {filesize} bytes")

        # Open the avatar file asynchronously
        async with aiofiles.open(avatar_file_path, "rb") as image_file:
            # Upload the avatar image to the Matrix server
            logger.debug(f"Uploading avatar for resident {resident_id}")
            upload_response = await _client.upload(
                image_file, content_type=content_type, filesize=filesize
            )

            # Check if the upload was successful
            if isinstance(upload_response, UploadResponse):
                mxc_url = upload_response.content_uri
                logger.info(f"Avatar uploaded successfully. URL: {mxc_url}")

                # Set the avatar using the uploaded URL
                logger.debug(f"Setting avatar URL for resident {resident_id}")
                set_avatar_response = await _client.set_avatar(mxc_url)
                avatar_url = await _client.get_avatar()
                _settings.avatar_http_url = await _client.mxc_to_http(avatar_url.avatar_url)
                resident_settings_update_sync_save(resident_id, avatar_http_url = avatar_url)
                logger.info("Avatar updated successfully.")
                update_resident_json_list(resident_id=resident_id)
                return CrudStatus.SUCCESS
            else:
                logger.error(f"Failed to upload avatar: {upload_response}")
                return CrudStatus.ERROR

    except Exception as e:
        logger.error(f"An error occurred while updating avatar for resident {resident_id}: {e}", exc_info=True)
        return CrudStatus.EXCEPTION
    
async def admin_login(resident_id: str, password: str)->LoginStatus:
    _star = Star()
    # logger = get_logger()
    try:
        # Check if the credentials are correct
        if resident_id == _star.messenger_admin_id and password == _star.messenger_admin_password:
            logger.info(f"Login successful for resident_id: {resident_id}")
            return LoginStatus.SUCCESS
        else:
            logger.warning(f"Login failed for resident_id: {resident_id}. Incorrect credentials.")
            return LoginStatus.ERROR
    except Exception as e:
        # Log the exception details
        logger.error(f"Exception occurred during login attempt for resident_id: {resident_id}. Error: {str(e)}")
        return LoginStatus.EXCEPTION

    
def get_uploaded_resident_document_names(resident_id: str) -> Any:
    try:
        logger.info(f"Loading document for resident: {resident_id}")
        
        # Initialize the Resident object and log the path
        _star = Star()
        resident_home_path = os.path.join(
            _star.star_residents_data_home,
            resident_id
        )
        
        logger.debug(f"Resident home path: {resident_home_path}")
        
        # Define folders to select and whether to exclude hidden files
        selected_folders = [_star.resident_document_subfolder]
        exclude_hidden = True  # Set to False to include hidden files/folders
        
        # Load the directory tree and handle success
        logger.info(f"Attempting to load documents...")
        counter, tree_data = utilities.load_directory_tree(resident_home_path, selected_folders, exclude_hidden)
        
        logger.info(f"Successfully loaded documents with {counter} items.")
        return CrudStatus.SUCCESS, tree_data

    except Exception as e:
        logger.exception(f"An unexpected error occurred while loading the documents for {resident_id}: {e}")
        return CrudStatus.EXCEPTION, str(e)  # Return exception status with the exception message

# PUBLIC FUNCTION
# Called by Fast API to delete an upladed file.
def delete_resident_document(resident_id: str, file_name: str) -> Tuple[CrudStatus, Optional[str]]:
    try:
        # Initialize Resident object
        _star = Star()
        # Construct the full path to the document
        file_full_path = os.path.join(
            _star.star_residents_data_home, 
            resident_id,
            _star.resident_document_subfolder, 
            file_name
        )

        logger.info(f"Attempting to delete document: {file_full_path}")

        # Check if the file exists before attempting deletion
        if os.path.exists(file_full_path):
            os.remove(file_full_path)
            logger.info(f"Document {file_name} deleted successfully for resident {resident_id}")
            return CrudStatus.SUCCESS, "Deleted successfully"
        else:
            logger.warning(f"Document {file_name} not found for resident {resident_id}")
            return CrudStatus.ERROR, "Document does not exist"
    
    except Exception as e:
        logger.error(f"Error deleting document for resident {resident_id}. Exception: {e}", exc_info=True)
        return CrudStatus.EXCEPTION, "Internal server error"
 






##################Sample data######################

# single user data retuend by messenger server, example for better unsetarnding: {
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

# Sample data: all_users =
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


