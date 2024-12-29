from nio import UploadResponse, ProfileSetAvatarResponse
import mimetypes, re, os, requests, json, aiofiles, aiohttp, shutil
from typing import List, Dict, Union, Any
from starlette import status
import bihua_one_star, messenger_resident, utilities
from bihua_one_star import Star
from messenger_resident import Resident
from messenger_group import Group
from bihua_logging import get_logger
from status_definitions import RegisterStatus, CheckCrudStatus, LoginStatus, CrudStatus
from pydantic import BaseModel, Field
from fastapi import UploadFile, HTTPException

logger = get_logger()

def is_valid_username(username) -> bool:
    pattern = r'^[a-zA-Z][a-zA-Z0-9]*$'
    
    # Use re.match to see if the entire username matches the pattern
    if re.match(pattern, username):
        return True
    else:
        return False


class AdminLoginRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, max_length=100, description="The unique ID of the resident")
    password: str = Field(..., min_length=8, max_length=100, description="The password for the resident account")
    
# assume lists of residents, groups, llm_models are there alreasy (start this bihua module's fastapi service)
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


# access_token should have admin access
# return list's name field is id.
#
# _synapse/admin/v2/users
class GetAllUsersRequest(BaseModel):
    base_url: str = Field(..., min_length=1, description="The base URL of your Synapse server")
    access_token: str = Field(..., min_length=1, description="The access token for authenticating the request")
    limit: int = Field(default=10, ge=1, description="Number of users to fetch per request")
def get_all_users(base_url, access_token, limit=10) -> List[dict]:
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


# use synapse API to register a user
# _synapse/admin/v2/users/{resident_id_to_be_created}
class RegisterUserRequest(BaseModel):
    username: str = Field(..., min_length=1, description="The username for the new user")
    password: str = Field(..., min_length=8, max_length=100, description="The password for the new user account")
    homeserver_url: str = Field(..., min_length=1, description="The URL of the homeserver")
async def register_user(username: str, password: str, homeserver_url: str) -> Dict[str, Union[str, RegisterStatus]]:
    if not is_valid_username(username):
        return {"status": RegisterStatus.ERROR, "code": RegisterStatus.INVALID_USERNAME, "message": "Invalid username"}

    resident_id_to_be_created = "@" + username + ":" + utilities.extract_homeserver_name(homeserver_url)
    star_settings = Star()

    admin_resident = Resident(star_settings.messenger_admin_id)
    base_url = star_settings.messenger_server_url
    url = f"{base_url}/_synapse/admin/v2/users/{resident_id_to_be_created}"
    admin_access_token = admin_resident.access_token

    headers = {
        "Authorization": f"Bearer {admin_access_token}"
    }

    # Check if the user already exists
    check_response = requests.get(url, headers=headers)

    if check_response.status_code == 200:  # User exists
        return {"status": RegisterStatus.ERROR, "code": RegisterStatus.USER_EXISTS, "message": "User already exists"}

    # Proceed to create the user if it doesn't exist
    data = {
        "password": password,
        "display_name": username,
        "admin": True,
        "deactivated": False,
    }

    try:
        # Create the user via PUT request
        response = requests.put(url, json=data, headers=headers)

        if response.status_code == 200:  # User created successfully
            # Fetch the user data immediately after creation
            user_data_url = f"{base_url}/_synapse/admin/v2/users/{resident_id_to_be_created}"
            user_data_response = requests.get(user_data_url, headers=headers)

            if user_data_response.status_code == 200:
                # Successfully fetched user data
                user_data = user_data_response.json()
                # save data to users profile json and update total user list
                resident_created = Resident(resident_id=resident_id_to_be_created)
                resident_created.messenger_client.login(password=password)

                # update function also saves data
                messenger_resident.resident_settings_update(
                    resident_id= resident_id_to_be_created,
                    display_name=user_data["displayname"],              # Update display name
                    email="",                # Update email
                    last_login_timestamp_ms=0,        # Update last login timestamp
                    last_sync_timestamp_ms=0,         # Update last sync timestamp
                    avatar_http_url=user_data["avatar_url"],  # Update avatar URL
                    username=username,                      # Update username
                    homeserver=homeserver_url,                        # Update homeserver_url
                    access_token=resident_created.messenger_client.access_token,              # Update access token
                    password=password,                      # Update password
                    agent="human",                                # Update agent (e.g., "agent" or "human")
                    role="admin",                                 # Update role (e.g., "admin" or "not")
                    state="active",                               # Update state (e.g., "active" or "not")
                    profile_text_path=resident_created.profile_text_path, # Update profile text path
                    profile_json_path=resident_created.profile_json_path # Update profile JSON path
                )

                # update the whole list
                bihua_one_star.append_resident_json_list(resident_id=resident_id_to_be_created)


                return {
                    "status": RegisterStatus.SUCCESS,
                    "message": "User created successfully",
                    "user_data": user_data  # Return the user data here
                }
            else:
                return {"status": RegisterStatus.ERROR, "code": RegisterStatus.FETCH_FAILED, "message": f"Failed to fetch user data: {user_data_response.status_code} - {user_data_response.text}"}

        else:
            return {"status": RegisterStatus.ERROR, "code": RegisterStatus.CREATION_FAILED, "message": f"Failed to create user: {response.status_code} - {response.text}"}

    except Exception as e:
        return {"status": RegisterStatus.ERROR, "code": RegisterStatus.EXCEPTION, "message": f"Error: {str(e)}"}
    
class ChangeUserPasswordRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose password is to be changed")
    new_password: str = Field(..., min_length=8, max_length=100, description="The new password for the resident account")
async def change_user_password(resident_id: str, new_password: str):
    try:
        resident = Resident(resident_id)
        admin_resident = Resident(resident.resident_star.messenger_admin_id)

        # If the new password is the same as the current password, no need to proceed
        if new_password == resident.password:
            logger.info(f"Password for resident {resident_id} is already up-to-date.")
            return CheckCrudStatus.NO_CHANGE  # No action needed

        # Prepare the data for the password change
        data = {"password": new_password}
        base_url = resident.resident_star.messenger_server_url
        
        # Construct the API URL
        url = f"{base_url}/_synapse/admin/v2/users/{resident_id}"

        # Set up the headers with the admin's access token
        headers = {"Authorization": f"Bearer {admin_resident.access_token}"}
        
        # Make the PUT request to change the password
        response = requests.put(url, json=data, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            resident.password = new_password
            messenger_resident.resident_settings_update(resident_id = resident_id, password = new_password)


            resident.profile_json_path
            bihua_one_star.update_resident_json_list(resident_id=resident_id)
            logger.info(f"Password for resident {resident_id} changed successfully.")
            return CheckCrudStatus.SUCCESS
        else:
            # Log the failure status
            logger.error(f"Failed to change password for resident {resident_id}. HTTP Status: {response.status_code}")
            return CheckCrudStatus.ERROR  # Return an error status

    except requests.exceptions.RequestException as e:
        # Log any exceptions that occur during the request
        logger.error(f"An error occurred while changing the password for {resident_id}: {e}")
        return CheckCrudStatus.EXCEPTION  # Return exception status to indicate an error occurred
    

class ChangeUserDisplayNameRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose display name is to be changed")
    new_displayname: str = Field(..., min_length=1, description="The new display name for the resident")
async def change_user_display_name(resident_id: str, new_displayname: str) -> str:
    try:
        # Initialize the resident and admin resident objects
        msg_resident = Resident(resident_id)

        # If the new display name is the same as the current display name, no need to proceed
        if msg_resident.display_name == new_displayname:
            logger.info(f"Display name for resident {resident_id} is already up-to-date.")
            return CheckCrudStatus.NO_CHANGE  # No action needed

        # Prepare the data for the display name change
        data = {"displayname": new_displayname}
        base_url = msg_resident.resident_star.messenger_server_url
        
        # Construct the API URL
        url = f"{base_url}/_synapse/admin/v2/users/{resident_id}"

        # Initialize the admin resident for authorization
        admin_resident = Resident(msg_resident.resident_star.messenger_admin_id)
        headers = {"Authorization": f"Bearer {admin_resident.access_token}"}
        
        # Make the PUT request to change the display name
        response = requests.put(url, json=data, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            msg_resident.display_name = new_displayname

            # Update the resident settings and JSON list after display name change
            messenger_resident.resident_settings_update(resident_id=resident_id, display_name=new_displayname)
            bihua_one_star.update_resident_json_list(resident_id=resident_id)
            
            logger.info(f"Display name for resident {resident_id} changed successfully.")
            return CheckCrudStatus.SUCCESS
        else:
            # Log the failure status
            logger.error(f"Failed to change display name for resident {resident_id}. HTTP Status: {response.status_code}")
            return CheckCrudStatus.ERROR  # Return an error status

    except requests.exceptions.RequestException as e:
        # Log any exceptions that occur during the request
        logger.error(f"An error occurred while changing the display name for {resident_id}: {e}")
        return CheckCrudStatus.EXCEPTION  # Return exception status to indicate an error occurred

class ChangeUserTypeRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose agent type is to be changed")
    new_agent_type: str = Field(..., min_length=1, description="The new agent type for the resident")
async def change_user_type(resident_id, new_agent_type: str):
    try:
        # Fetch the resident's current data
        msg_resident = Resident(resident_id)
        
        # Check if the new agent type is different from the current one
        if new_agent_type != msg_resident.agent:
            # Update the resident's agent type in the system
            messenger_resident.resident_settings_update(resident_id=resident_id, agent=new_agent_type)
            
            # Update the JSON list for the resident
            bihua_one_star.update_resident_json_list(resident_id=resident_id)
            
            logger.info(f"Agent type for resident {resident_id} changed successfully to {new_agent_type}.")
            return CheckCrudStatus.SUCCESS
        
        # If the new agent type is the same as the old one
        logger.info(f"No change in agent type for resident {resident_id}. The agent is already {new_agent_type}.")
        return CheckCrudStatus.NO_CHANGE
    
    except Exception as e:
        # Log the error and raise a more descriptive message
        logger.error(f"Failed to change agent type for resident {resident_id}: {str(e)}")
        return CheckCrudStatus.EXCEPTION


class ChangeUserRoleRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose role is to be changed")
    new_role: str = Field(..., min_length=1, description="The new role for the resident")
async def change_user_role(resident_id: str, new_role: str) -> str:
    try:
        # Initialize the resident object
        msg_resident = Resident(resident_id)

        # If the new role is the same as the current role, no need to proceed
        if msg_resident.role == new_role:
            logger.info(f"Role for resident {resident_id} is already up-to-date.")
            return CheckCrudStatus.NO_CHANGE  # No action needed

        # Prepare the data for the role change
        if new_role == "admin":
            data = {"admin": True}
        else:
            data = {"admin": False}

        base_url = msg_resident.resident_star.messenger_server_url
        
        # Construct the API URL for the role change request
        url = f"{base_url}/_synapse/admin/v2/users/{resident_id}"

        # Initialize the admin resident for authorization
        admin_resident = Resident(msg_resident.resident_star.messenger_admin_id)
        headers = {"Authorization": f"Bearer {admin_resident.access_token}"}
        
        # Make the PUT request to change the role
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=data, headers=headers) as response:
                # Check if the request was successful
                if response.status == 200:
                    msg_resident.role = new_role  # Update the resident's role

                    # Update the resident settings and JSON list after role change
                    messenger_resident.resident_settings_update(resident_id=resident_id, role=new_role)
                    bihua_one_star.update_resident_json_list(resident_id=resident_id)
                    
                    logger.info(f"Role for resident {resident_id} changed successfully.")
                    return CheckCrudStatus.SUCCESS
                else:
                    # Log the failure status with response text for more context
                    response_text = await response.text()
                    logger.error(f"Failed to change role for resident {resident_id}. "
                                  f"HTTP Status: {response.status}, Response: {response_text}")
                    return CheckCrudStatus.ERROR  # Return an error status

    except aiohttp.ClientError as e:
        # Log any exceptions that occur during the request
        logger.error(f"An error occurred while changing the role for {resident_id}: {e}")
        return CheckCrudStatus.EXCEPTION  # Return exception status to indicate an error occurred

class ChangeUserStateRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose state is to be changed")
    new_state: str = Field(..., min_length=1, description="The new state for the resident")
async def change_user_state(resident_id: str, new_state: str) -> str:
    try:
        # Initialize the resident object
        msg_resident = Resident(resident_id)

        # If the new state is the same as the current state, no need to proceed
        if msg_resident.state == new_state:
            logger.info(f"State for resident {resident_id} is already up-to-date.")
            return CheckCrudStatus.NO_CHANGE  # No action needed

        # Prepare the data for the state change
        if new_state == "active":
            data = {"deactivated": False}
        else:
            data = {"deactivated": True}

        base_url = msg_resident.resident_star.messenger_server_url
        
        # Construct the API URL for the state change request
        url = f"{base_url}/_synapse/admin/v2/users/{resident_id}"

        # Initialize the admin resident for authorization
        admin_resident = Resident(msg_resident.resident_star.messenger_admin_id)
        headers = {"Authorization": f"Bearer {admin_resident.access_token}"}
        
        # Make the PUT request to change the state
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=data, headers=headers) as response:
                # Check if the request was successful
                if response.status == 200:
                    msg_resident.state = new_state  # Update the resident's state

                    # Update the resident settings and JSON list after state change
                    messenger_resident.resident_settings_update(resident_id=resident_id, state=new_state)
                    bihua_one_star.update_resident_json_list(resident_id=resident_id)
                    
                    logger.info(f"State for resident {resident_id} changed successfully.")
                    return CheckCrudStatus.SUCCESS
                else:
                    # Log the failure status with response text for more context
                    response_text = await response.text()
                    logger.error(f"Failed to change state for resident {resident_id}. "
                                  f"HTTP Status: {response.status}, Response: {response_text}")
                    return CheckCrudStatus.ERROR  # Return an error status

    except aiohttp.ClientError as e:
        # Log any exceptions that occur during the request
        logger.error(f"An error occurred while changing the state for {resident_id}: {e}")
        return CheckCrudStatus.EXCEPTION  # Return exception status to indicate an error occurred

# from client, we first upload avatar file to messenger server. Then we call this function to change
# avatar in mesenger
class UpdateUserAvatarInMessengerRequest(BaseModel):
    resident_id: str = Field(..., min_length=1, description="The ID of the resident whose avatar is to be updated")
    avatar_file_path: str = Field(..., min_length=1, description="The file path of the new avatar image")

async def update_user_avatar_in_messenger(resident_id: str, avatar_file_path: str):
    msg_resident = Resident(resident_id)
    logger.info(f"Attempting to update avatar for resident ID: {resident_id}")

    try:
        # Log in to the Messenger client
        logger.debug(f"Logging in to the Messenger client for resident {resident_id}")
        await msg_resident.messenger_client.login(msg_resident.password)

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
            upload_response = await msg_resident.messenger_client.upload(
                image_file, content_type=content_type, filesize=filesize
            )

            # Check if the upload was successful
            if isinstance(upload_response, UploadResponse):
                mxc_url = upload_response.content_uri
                logger.info(f"Avatar uploaded successfully. URL: {mxc_url}")

                # Set the avatar using the uploaded URL
                logger.debug(f"Setting avatar URL for resident {resident_id}")
                set_avatar_response = await msg_resident.messenger_client.set_avatar(mxc_url)
                avatar_url = await msg_resident.messenger_client.get_avatar()
                avatar_http_url = await msg_resident.messenger_client.mxc_to_http(avatar_url.avatar_url)

                # Check if the avatar was set successfully
                if isinstance(set_avatar_response, ProfileSetAvatarResponse):
                    logger.info("Avatar updated successfully.")
                    messenger_resident.resident_settings_update(resident_id, avatar_http_url=avatar_http_url)
                    bihua_one_star.update_resident_json_list(resident_id)
                    return CrudStatus.SUCCESS
                else:
                    logger.error(f"Failed to set avatar: {set_avatar_response}")
                    return CrudStatus.ERROR
            else:
                logger.error(f"Failed to upload avatar: {upload_response}")
                return CrudStatus.ERROR

    except Exception as e:
        logger.error(f"An error occurred while updating avatar for resident {resident_id}: {e}", exc_info=True)
        return CrudStatus.EXCEPTION
    

async def update_group_avatar_in_messenger(resident_id:str, group_id: str, avatar_file_path: str):
    logger.info(f"Attempting to update avatar for room ID: {group_id}")
    _resident = Resident(resident_id)
    try:
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
            logger.debug(f"Uploading avatar for room {group_id}")
            upload_response = await _resident.messenger_client.upload(
                image_file, content_type=content_type, filesize=filesize
            )

            # Check if the upload was successful
            if isinstance(upload_response, UploadResponse):
                mxc_url = upload_response.content_uri
                logger.info(f"Avatar uploaded successfully. URL: {mxc_url}")

                # Set the avatar using the uploaded URL
                logger.debug(f"Setting avatar URL for room {group_id}")
                set_avatar_response = await _resident.messenger_client.room_put_state(
                    group_id, 
                    "m.room.avatar", 
                    {"url": mxc_url}
                )

                # Check if the avatar was set successfully
                if isinstance(set_avatar_response, ProfileSetAvatarResponse):
                    logger.info("Room avatar updated successfully.")
                    return CrudStatus.SUCCESS
                else:
                    logger.error(f"Failed to set room avatar: {set_avatar_response}")
                    return CrudStatus.ERROR
            else:
                logger.error(f"Failed to upload avatar: {upload_response}")
                return CrudStatus.ERROR

    except Exception as e:
        logger.error(f"An error occurred while updating avatar for room {group_id}: {e}", exc_info=True)
        return CrudStatus.EXCEPTION


def load_group_profile(group_id):

    # Create Resident instance
    _group = Group(group_id)
    
    try:
        # Try to read the resident's profile
        with open(_group.settings.profile_text_path, 'r') as file:
            profile_text = file.read()
        
        # Log success and return the profile data
        logger.info(f"Successfully loaded profile for resident {group_id}")
        return CrudStatus.SUCCESS, profile_text

    except FileNotFoundError:
        # Specific error for file not found
        logger.error(f"Profile file not found for resident {group_id}: {_group.settings.profile_text_path}")
        return CrudStatus.ERROR, f"Profile file not found for resident {group_id}"

    except Exception as e:
        # Log unexpected errors
        logger.exception(f"Unexpected error occurred while loading profile for resident {group_id}: {str(e)}")
        return CrudStatus.EXCEPTION, f"An error occurred: {str(e)}"



def save_group_profile(group_id, profile_text):

    # Create Resident instance
    _group = Group(group_id)

    try:
        # Try to save the profile text to the file
        with open(_group.settings.profile_text_path, 'w') as file:
            file.write(profile_text)

        # Log success and return status
        logger.info(f"Successfully saved profile for resident {group_id}")
        return CrudStatus.SUCCESS, "Success"

    except PermissionError:
        # Handle permission errors
        logger.error(f"Permission denied while saving profile for resident {group_id}: {_group.settings.profile_text_path}")
        return CrudStatus.ERROR, f"Permission denied for file: {_group.profile_text_path}"

    except FileNotFoundError:
        # Handle case where the file is not found
        logger.error(f"Profile path not found for resident {group_id}: {_group.settings.profile_text_path}")
        return CrudStatus.ERROR, f"Profile path not found: {_group.settings.profile_text_path}"

    except Exception as e:
        # Log any unexpected exceptions
        logger.exception(f"Unexpected error occurred while saving profile for resident {group_id}: {str(e)}")
        return CrudStatus.EXCEPTION, f"An error occurred: {str(e)}"


def load_resident_profile(resident_id):

    # Create Resident instance
    _resident = Resident(resident_id)
    
    try:
        # Try to read the resident's profile
        with open(_resident.settings.profile_text_path, 'r') as file:
            profile_data = file.read()
        
        # Log success and return the profile data
        logger.info(f"Successfully loaded profile for resident {resident_id}")
        return CrudStatus.SUCCESS, profile_data

    except FileNotFoundError:
        # Specific error for file not found
        logger.error(f"Profile file not found for resident {resident_id}: {_resident.settings.profile_text_path}")
        return CrudStatus.ERROR, f"Profile file not found for resident {resident_id}"

    except Exception as e:
        # Log unexpected errors
        logger.exception(f"Unexpected error occurred while loading profile for resident {resident_id}: {str(e)}")
        return CrudStatus.EXCEPTION, f"An error occurred: {str(e)}"


def save_resident_profile(resident_id, profile_text):

    # Create Resident instance
    _resident = Resident(resident_id)

    try:
        # Try to save the profile text to the file
        with open(_resident.settings.profile_text_path, 'w') as file:
            file.write(profile_text)

        # Log success and return status
        logger.info(f"Successfully saved profile for resident {resident_id}")
        return CrudStatus.SUCCESS, "Success"

    except PermissionError:
        # Handle permission errors
        logger.error(f"Permission denied while saving profile for resident {resident_id}: {_resident.settings.profile_text_path}")
        return CrudStatus.ERROR, f"Permission denied for file: {_resident.settings.profile_text_path}"

    except FileNotFoundError:
        # Handle case where the file is not found
        logger.error(f"Profile path not found for resident {resident_id}: {_resident.settings.profile_text_path}")
        return CrudStatus.ERROR, f"Profile path not found: {_resident.settings.profile_text_path}"

    except Exception as e:
        # Log any unexpected exceptions
        logger.exception(f"Unexpected error occurred while saving profile for resident {resident_id}: {str(e)}")
        return CrudStatus.EXCEPTION, f"An error occurred: {str(e)}"


def delete_resident_document(resident_id: str, file_name: str):
    try:
        # Initialize Resident object
        _resident = Resident(resident_id)

        # Construct the full path to the document
        file_full_path = os.path.join(
            _resident.resident_star.star_residents_data_home, 
            resident_id,
            _resident.resident_star.resident_document_subfolder, 
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
    

def delete_group_document(group_id: str, file_name: str):
    """
    Delete a document for a specific group.

    Args:
        group_id (str): The ID of the group (resident).
        file_name (str): The name of the file to delete.

    Returns:
        tuple: A tuple containing the status and message.
            - CrudStatus.SUCCESS, "Deleted successfully" on successful deletion
            - CrudStatus.ERROR, "Document does not exist" if the document is not found
            - CrudStatus.EXCEPTION, "Internal server error" if an exception occurs
    """
    try:
        # Initialize Group object using the provided group_id
        _group = Group(group_id)

        # Construct the full path to the document
        file_full_path = os.path.join(
            _group.group_star.star_groups_data_home,  # Base directory
            group_id,                                 # Group ID (subfolder)
            _group.group_star.group_document_subfolder, # Document subfolder
            file_name                                  # Document name
        )

        logger.info(f"Attempting to delete document: {file_full_path}")

        # Check if the file exists before attempting deletion
        if os.path.exists(file_full_path):
            # Delete the file if it exists
            os.remove(file_full_path)
            logger.info(f"Document {file_name} deleted successfully for group {group_id}")
            return CrudStatus.SUCCESS, "Deleted successfully"
        else:
            # Log a warning if the file does not exist
            logger.warning(f"Document {file_name} not found for group {group_id}")
            return CrudStatus.ERROR, "Document does not exist"
    
    except Exception as e:
        # Log any unexpected exceptions
        logger.error(f"Error deleting document for group {group_id}. Exception: {e}", exc_info=True)
        return CrudStatus.EXCEPTION, "Internal server error"
    
    
def get_uploaded_resident_document_names(resident_id: str) -> Any:
    try:
        logger.info(f"Loading document for resident: {resident_id}")
        
        # Initialize the Resident object and log the path
        _resident = Resident(resident_id)
        resident_home_path = os.path.join(
            _resident.resident_star.star_residents_data_home,
            resident_id,
            _resident.resident_star.resident_document_subfolder
        )
        
        logger.debug(f"Resident home path: {resident_home_path}")
        
        # Define folders to select and whether to exclude hidden files
        selected_folders = ["documents"]
        exclude_hidden = True  # Set to False to include hidden files/folders
        
        # Load the directory tree and handle success
        logger.info(f"Attempting to load directory tree from {resident_home_path}...")
        counter, tree_data = utilities.load_directory_tree(resident_home_path, selected_folders, exclude_hidden)
        
        logger.info(f"Successfully loaded directory tree with {counter} items.")
        return CrudStatus.SUCCESS, tree_data

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return CrudStatus.ERROR, str(e)  # Return error status with the error message

    except PermissionError as e:
        logger.error(f"Permission error when accessing {resident_id}: {e}")
        return CrudStatus.ERROR, str(e)  # Return error status with the error message

    except Exception as e:
        logger.exception(f"An unexpected error occurred while loading the document for {resident_id}: {e}")
        return CrudStatus.EXCEPTION, str(e)  # Return exception status with the exception message

def get_upladed_group_document_names(group_id: str) -> Any:
    try:
        logger.info(f"Loading document for group: {group_id}")
        
        # Initialize the Resident object and log the path
        _group = Group(group_id)
        group_home_path = os.path.join(
            _group.group_star.star_groups_data_home,
            group_id,
            _group.group_star.group_document_subfolder
        )
        
        logger.debug(f"Resident home path: {group_home_path}")
        
        # Define folders to select and whether to exclude hidden files
        selected_folders = ["documents"]
        exclude_hidden = True  # Set to False to include hidden files/folders
        
        # Load the directory tree and handle success
        logger.info(f"Attempting to load directory tree from {group_home_path}...")
        counter, tree_data = utilities.load_directory_tree(group_home_path, selected_folders, exclude_hidden)
        
        logger.info(f"Successfully loaded directory tree with {counter} items.")
        return CrudStatus.SUCCESS, tree_data

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return CrudStatus.ERROR, str(e)  # Return error status with the error message

    except PermissionError as e:
        logger.error(f"Permission error when accessing {group_id}: {e}")
        return CrudStatus.ERROR, str(e)  # Return error status with the error message

    except Exception as e:
        logger.exception(f"An unexpected error occurred while loading the document for {group_id}: {e}")
        return CrudStatus.EXCEPTION, str(e)  # Return exception status with the exception message


def upload_resident_document(resident_id: str, file_to_be_uploaded: UploadFile):
    try:
        _resident = Resident(resident_id)

        # Define document folder path
        document_folder = os.path.join(
            _resident.resident_star.star_residents_data_home,
            resident_id,
            _resident.resident_star.resident_document_subfolder
        )

        # Ensure the document folder exists
        os.makedirs(document_folder, exist_ok=True)

        # Define the file destination path
        file_destination_path = os.path.join(
            document_folder,
            file_to_be_uploaded.filename
        )

        # Check if the file already exists to prevent overwriting
        if os.path.exists(file_destination_path):
            logger.warning(f"File '{file_to_be_uploaded.filename}' already exists in {document_folder}.")
            return {
                "message": "File already exists",
                "status": CrudStatus.ERROR,
                "file": file_to_be_uploaded.filename
            }

        # Write the uploaded file to the destination
        with open(file_destination_path, 'wb') as file:
            shutil.copyfileobj(file_to_be_uploaded.file, file)

        logger.info(f"File '{file_to_be_uploaded.filename}' uploaded successfully to {file_destination_path}.")
        
        return {
            "message": "File uploaded successfully",
            "status": CrudStatus.SUCCESS,
            "file": file_to_be_uploaded.filename
        }

    except Exception as e:
        logger.error(f"Error processing file upload: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
def upload_group_document(group_id: str, file_to_be_uploaded: UploadFile):
    try:
        _group = Group(group_id)

        # Define document folder path
        document_folder = os.path.join(
            _group.group_star.star_groups_data_home,
            group_id,
            _group.group_star.group_document_subfolder
        )

        # Ensure the document folder exists
        os.makedirs(document_folder, exist_ok=True)

        # Define the file destination path
        file_destination_path = os.path.join(
            document_folder,
            file_to_be_uploaded.filename
        )

        # Check if the file already exists to prevent overwriting
        if os.path.exists(file_destination_path):
            logger.warning(f"File '{file_to_be_uploaded.filename}' already exists in {document_folder}.")
            return {
                "message": "File already exists",
                "status": CrudStatus.ERROR,
                "file": file_to_be_uploaded.filename
            }

        # Write the uploaded file to the destination
        with open(file_destination_path, 'wb') as file:
            shutil.copyfileobj(file_to_be_uploaded.file, file)

        logger.info(f"File '{file_to_be_uploaded.filename}' uploaded successfully to {file_destination_path}.")
        
        return {
            "message": "File uploaded successfully",
            "status": CrudStatus.SUCCESS,
            "file": file_to_be_uploaded.filename
        }

    except Exception as e:
        logger.error(f"Error processing file upload: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

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

def collect_resident_list()->CrudStatus:
    """Collect all resident data and save to JSON file."""
    _star = Star()
    try:
        resident_list_json_file_path = _star.resident_list_json_path
        residents_data_home = _star.star_residents_data_home
        resident_profile_subfolder_name = _star.resident_profile_subfolder
        resident_list = []

        logger.info(f"Starting resident list collection from {residents_data_home}")

        for path in os.listdir(residents_data_home):
            full_path = os.path.join(residents_data_home, path, resident_profile_subfolder_name)
            if os.path.isdir(full_path) and path.startswith("@"):
                resident_json_file_path = os.path.join(full_path, f"{path}.json")
                try:
                    with open(resident_json_file_path, 'r') as f:
                        resident_json = json.load(f)
                        resident_list.append(resident_json)
                    logger.debug(f"Added resident data from {resident_json_file_path}")
                except Exception as e:
                    logger.error(f"Error reading {resident_json_file_path}: {e}")
                    continue  # Proceed with other files even if one fails

        resident_list_json = json.dumps(resident_list, indent=4)
        with open(resident_list_json_file_path, 'w') as f:
            f.write(resident_list_json)

        logger.info(f"Resident list successfully saved to {resident_list_json_file_path}")
        return CrudStatus.SUCCESS

    except Exception as e:
        logger.error(f"Error in collect_resident_list: {e}")
        return CrudStatus.EXCEPTION


def get_group_list() -> tuple[CrudStatus, dict]:
    """Get the group list from the JSON file."""
    _star = Star()
    file_path = _star.group_list_json_path
    try:
        logger.info(f"Attempting to load group list from {file_path}")
        list_status, data = utilities.read_json_file(file_path)
        
        if list_status == CrudStatus.SUCCESS:
            logger.info(f"Successfully loaded group list from {file_path}")
            return CrudStatus.SUCCESS, data
        
        logger.error(f"Failed to load group list from {file_path}. Status: {list_status}")
        return CrudStatus.ERROR, {"error": "Failed to load group list"}

    except Exception as e:
        logger.error(f"Exception occurred while getting group list from {file_path}: {e}")
        return CrudStatus.EXCEPTION, {"error": f"Exception: {e}"}


def collect_group_list()->CrudStatus:
    """Collect all group data and save to JSON file."""
    _star = Star()
    try:
        group_list_json_file_path = _star.group_list_json_path
        groups_data_home = _star.star_groups_data_home
        group_profile_subfolder_name = _star.group_profile_subfolder
        group_list = []

        logger.info(f"Starting group list collection from {groups_data_home}")

        for path in os.listdir(groups_data_home):
            full_path = os.path.join(groups_data_home, path, group_profile_subfolder_name)
            if os.path.isdir(full_path) and path.startswith("!"):
                group_json_file_path = os.path.join(full_path, f"{path}.json")
                try:
                    with open(group_json_file_path, 'r') as f:
                        group_json = json.load(f)
                        group_list.append(group_json)
                    logger.debug(f"Added group data from {group_json_file_path}")
                except Exception as e:
                    logger.error(f"Error reading {group_json_file_path}: {e}")
                    continue  # Proceed with other files even if one fails

        group_list_json = json.dumps(group_list, indent=4)
        with open(group_list_json_file_path, 'w') as f:
            f.write(group_list_json)

        logger.info(f"Group list successfully saved to {group_list_json_file_path}")
        return CrudStatus.SUCCESS

    except Exception as e:
        logger.error(f"Error in collect_group_list: {e}")
        return CrudStatus.EXCEPTION


def get_llm_model_list():
    """Get the LLM list from the JSON file."""
    _star = Star()
    file_path = _star.llm_model_list_json_path
    model_status, data = utilities.read_json_file(file_path)
    if model_status == CrudStatus.SUCCESS:
        return data
    return {"error": "Failed to load LLM list"}

def fetch_llm_model_by_id(model_id):
    """Get the LLM model details by model_id from the JSON file."""
    _star = Star()
    file_path = _star.llm_model_list_json_path
    
    logger.info(f"Attempting to load LLM model list from: {file_path}")
    
    try:
        # Try reading the JSON file
        data, status = utilities.read_json_file(file_path)
        
        if status == CrudStatus.SUCCESS:
            # Find the model with the given model_id in the 'models' list
            logger.debug(f"Searching for model with id {model_id}")
            model = next((model for model in data['models'] if model['model_id'] == model_id), None)
            
            if model:
                logger.info(f"Model with id {model_id} found.")
                return model
            else:
                logger.warning(f"Model with id {model_id} not found.")
                return {"error": f"Model with id {model_id} not found"}
        
        else:
            logger.error("Failed to load LLM model list: status was not 'SUCCESS'.")
            return {"error": "Failed to load LLM list"}
    
    except Exception as e:
        # Catch any unexpected errors
        logger.exception(f"An error occurred while retrieving the model with id {model_id}: {e}")
        return {"error": f"An error occurred: {str(e)}"}

# def create_group(room_name, room_topic=""):
#     _star = Star()
#     logger.info("Attempting to create a room with name: %s", room_name)

#     create_room_url = f'{_star.messenger_server_url}/_matrix/client/r0/createRoom'

#     # Data to send in the POST request to create the room
#     room_data = {
#         "visibility": "public",  # 'public', 'private', or 'restricted'
#         "preset": "public_chat",  # 'private_chat', 'public_chat', or 'trusted_private_chat'
#         "name": room_name,        # Room name
#         "topic": room_topic,      # Optional room topic
#         "invite": [],             # List of user IDs to invite (empty in this case)
#         "room_version": "v1",     # Matrix room version (usually 'v1')
#     }

#     headers = {
#         'Authorization': f'Bearer {_star.messenger_admin_access_token}',
#         'Content-Type': 'application/json',
#     }

#     try:
#         # Send the POST request to create the room
#         response = requests.post(create_room_url, headers=headers, data=json.dumps(room_data))

#         # Check the response
#         if response.status_code == 200:
#             # Room created successfully, extract room ID
#             room_id = response.json().get('room_id')
#             logger.info("Room created successfully. Room ID: %s", room_id)
#             return CheckCrudStatus.SUCCESS, room_id
#         else:
#             error_message = f"Failed to create room. Status code: {response.status_code}, Response: {response.text}"
#             logger.error(error_message)
#             return CrudStatus.ERROR, error_message
        
#     except requests.exceptions.RequestException as e:
#         # Catch request-related exceptions (e.g., network errors, invalid responses)
#         error_message = f"RequestException occurred: {e}"
#         logger.exception(error_message)  # Logs the full stack trace
#         return CrudStatus.EXCEPTION, None
    
#     except Exception as e:
#         # Catch any other exceptions that might occur
#         error_message = f"Unexpected error occurred: {e}"
#         logger.exception(error_message)  # Logs the full stack trace
#         return CrudStatus.EXCEPTION, None


# Set up logging




