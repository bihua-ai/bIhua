import re, os, json
from enum import Enum
from bihua_logging import get_logger
from status_definitions import RegisterStatus, CheckCrudStatus, LoginStatus, CrudStatus

logger = get_logger()

class RegisterStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    INVALID_USERNAME = "invalid_username"
    NO_PERMISSION = "no_permission"
    USER_EXISTS = "user_exists"
    CREATION_FAILED = "creation_failed"
    EXCEPTION = "exception"

class Status(Enum):
    SUCCESS = "success"
    NO_CHANGE = "new value and old value are the same. no need to update."
    ERROR = "error"
    EXCEPTION = "exception"

def is_valid_username(username) -> bool:
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]*$'
    return bool(re.match(pattern, username))

    
    # Use re.match to see if the entire username matches the pattern
    if re.match(pattern, username):
        return True
    else:
        return False

def split_resident_id(resident_id):
    """
    Splits a resident_id of the form (@username:servername) into username and servername.

    Args:
    - resident_id (str): The resident_id to split.

    Returns:
    - tuple: A tuple containing (username, servername).

    Raises:
    - ValueError: If the resident_id is not in the correct format.
    """
    # Regular expression to match the expected format
    pattern = r'^@([^:]+):(.+)$'
    
    # Check if the resident_id matches the expected pattern
    match = re.match(pattern, resident_id)
    
    if match:
        username, servername = match.groups()
        return username, servername
    else:
        return None, None

def split_group_id(group_id):
    """
    Splits a group_id of the form (!group_name:servername) into group_name and servername.

    Args:
    - group_id (str): The group_id to split.

    Returns:
    - tuple: A tuple containing (group_name, servername).

    Raises:
    - ValueError: If the group_id is not in the correct format.
    """
    # Regular expression to match the expected format
    pattern = r'^!([^:]+):(.+)$'
    
    # Check if the group_id matches the expected pattern
    match = re.match(pattern, group_id)
    
    if match:
        groupname, servername = match.groups()
        return groupname, servername
    else:
        return None, None

def extract_homeserver_name(homeserver: str) -> str:
    """
    Extracts the name of the homeserver by removing the 'http://' or 'https://' part, if present.

    Args:
        homeserver (str): The full homeserver URL or name.

    Returns:
        str: The homeserver name without 'http://' or 'https://'.
    """
    # Remove the scheme (http:// or https://) if it exists
    if homeserver.startswith("http://"):
        return homeserver[len("http://"):]
    elif homeserver.startswith("https://"):
        return homeserver[len("https://"):]
    
    # Return as-is if no scheme
    return homeserver

def load_directory_tree(resident_home_path, selected_folders, exclude_hidden=True, counter=1, top_level = True):
    """
    Recursively loads all folders and files into a JSON structure,
    marking folders, handling hidden files/folders, and allowing folder selection.

    Args:
        root_dir (str): The root directory to traverse.
        selected_folders (list): A list of folder names to be included.
            If empty, all folders are included.
        exclude_hidden (bool, optional): Whether to exclude hidden files and folders.
            Defaults to True.

    Returns:
        dict: A JSON-like dictionary representing the directory structure.
    """
    try:
        tree = {"id":str(counter), "name": os.path.basename(resident_home_path), "type": "directory", "children": []}
        counter = counter + 1

        for item in os.listdir(resident_home_path):
            if exclude_hidden and (item.startswith('.') or item in ('__pycache__', '.git')):
                continue

            full_path = os.path.join(resident_home_path, item)
            if os.path.isdir(full_path):
                if selected_folders or top_level==False:
                    # Include only folders in the selected list

                    if item in selected_folders or top_level==False:
                        
                        counter, sub_tree =  load_directory_tree(full_path, selected_folders, exclude_hidden, counter=counter, top_level=False)
                        tree["children"].append(sub_tree)
                else:
                    # Include all folders
                    tree["children"].append(load_directory_tree(full_path, selected_folders, exclude_hidden, top_level=False))
            else:
                # Add files with information about their type
                tree["children"].append({"id":str(counter), "name": item, "type": "file"})
                counter = counter + 1

        return counter, tree
    except Exception as e:
        # bihua_logging.bihua_logging(f"Error load_directory_tree: {e}", level=logging.ERROR)
        print(e)

    return None

def read_json_file(file_path):
    """Helper function to read a JSON file and handle errors."""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return CrudStatus.ERROR, None

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            logger.info(f"Successfully read the file: {file_path}")
            return CrudStatus.SUCCESS, data
    except Exception as e:
        logger.error(f"Failed to read the file {file_path}. Error: {e}")
        return CrudStatus.EXCEPTION, None


def update_env_file(field_name: str, value: str, env_file: str = '.env'):
    """Update the .env file with the new environment variable value."""
    updated = False
    
    # Check if the .env file exists
    if os.path.exists(env_file):
        with open(env_file, 'r') as file:
            lines = file.readlines()
        
        with open(env_file, 'w') as file:
            for line in lines:
                if line.startswith(f"{field_name}="):
                    file.write(f"{field_name}={value}\n")  # Update the variable
                    updated = True
                else:
                    file.write(line)
    
    # If the variable was not found, append it
    if not updated:
        with open(env_file, 'a') as file:
            file.write(f"{field_name}={value}\n")
    
    # Update the current process environment
    # os.environ[field_name] = value


def convert_mxc_to_url(mxc_url, base_url):
    """
    Converts an mxc:// URL to an HTTP(S) URL.
    
    :param mxc_url: The mxc:// URI (e.g., "mxc://example.com/abcdef1234567890")
    :param base_url: The base URL of the Matrix server (e.g., "https://matrix.example.com")
    :return: The regular HTTP(S) URL for the media file
    """
    if not mxc_url.startswith("mxc://"):
        raise ValueError("Invalid mxc URL")

    # Extract server_name and media_id
    parts = mxc_url[6:].split("/", 1)  # Remove "mxc://" and split by "/"
    if len(parts) != 2:
        raise ValueError("Invalid mxc URL format")

    server_name, media_id = parts
    return f"{base_url}/_matrix/media/v3/download/{server_name}/{media_id}"
    # return f"{base_url}/_matrix/media/r0/download/{server_name}/{media_id}"

from urllib.parse import quote

def encode_group_alias(room_alias):
    """
    Encodes a room alias for safe inclusion in a URL.

    Args:
        room_alias (str): The room alias to encode (e.g., '#group_001:messenger.b1.shuwantech.com').

    Returns:
        str: The URL-encoded room alias.
    """
    return quote(room_alias, safe="")

