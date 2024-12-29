from dotenv import load_dotenv
import os, json
from bihua_logging import get_logger
from status_definitions import CrudStatus
import utilities


logger = get_logger()

# load .env and create folders needed.
# iniit the Star class, all will be done: collection, directories.
class Star():
    star_entity_data_home: str
    star_residents_data_home: str
    star_groups_data_home: str
    star_log_path: str
    star_log_file_max_size: int
    star_log_file_backup_count: int

    resident_profile_subfolder: str
    resident_document_subfolder: str
    resident_chat_history_subfolder: str
    resident_list_json_path: str

    group_profile_subfolder: str
    group_document_subfolder: str
    group_chat_history_subfolder: str
    group_thread_subfolder: str
    group_list_json_path: str

    llm_model_list_json_path: str

    messenger_server_in_docker_url: str
    messenger_server_url: str
    messenger_server_name: str

    messenger_admin_id: str
    messenger_admin_password: str
    messenger_admin_access_token: str = ""


    # **data is here to support pydantic functions
    def __init__(self):

        logger.info("Initializing Star settings and directories.")
        try:
            # Load environment variables
            self.reload_settings()

            # Ensure required directories exist
            # folders are created
            log_dir = os.path.dirname(self.star_log_path)
            for path in [self.star_entity_data_home, self.star_residents_data_home, self.star_groups_data_home, log_dir]:
                os.makedirs(path, exist_ok=True)

            if not os.path.exists(self.resident_list_json_path):
                self.generate_resident_json_list()
            # if not os.path.exists(self.group_list_json_path):
            #     self.generate_group_json_list()

            # if not os.path.exists(self.resident_list_json_path) or os.path.getsize(self.resident_list_json_path) == 0:
            #     generate_resident_json_list()

            # if not os.path.exists(self.group_list_json_path) or os.path.getsize(self.group_list_json_path) == 0:
            #     generate_group_json_list()
            logger.info("Star initialization completed successfully.")
        except Exception as e:
            logger.exception(f"Error during Star initialization: {e}")
            raise

    def reload_settings(self):
        """Reload settings from the environment variables."""
        logger.info("Settings are reloading.")
        try:
            load_dotenv()
            self.star_entity_data_home = os.getenv("HOME_PATH_OF_DATA_OF_ENTITIES")
            self.star_residents_data_home = os.getenv("HOME_PATH_OF_DATA_OF_RESIDENTS")
            self.star_groups_data_home = os.getenv("HOME_PATH_OF_DATA_OF_GROUPS")
            self.star_log_path = os.getenv("STAR_LOG_PATH")
            self.star_log_file_max_size = int(os.getenv("STAR_LOG_FILE_MAX_SIZE"))
            self.star_log_file_backup_count = int(os.getenv("STAR_LOG_FILE_BACKUP_COUNT"))

            self.resident_profile_subfolder = os.getenv("RESIDENT_PROFILE_SUB_PATH")
            self.resident_document_subfolder = os.getenv("RESIDENT_DOCUMENT_SUB_PATH")
            self.resident_chat_history_subfolder = os.getenv("RESIDENT_CHAT_HISTORY_SUB_PATH")
            self.resident_list_json_path = os.getenv("STAR_RESIDENT_LIST_JSON_PATH")

            self.group_profile_subfolder = os.getenv("GROUP_PROFILE_SUB_PATH")
            self.group_document_subfolder = os.getenv("GROUP_DOCUMENT_SUB_PATH")
            self.group_chat_history_subfolder = os.getenv("GROUP__CHAT_HISTORY_SUB_PATH")
            self.group_thread_subfolder = os.getenv("THREAD_SUB_PATH")
            self.group_list_json_path = os.getenv("STAR_GROUP_LIST_JSON_PATH")

            self.llm_model_list_json_path = os.getenv("STAR_LLM_MODELS_LIST_JSON_PATH")

            self.messenger_server_in_docker_url = os.getenv("MESSENGER_SERVER_URL_IN_DOCKER")
            self.messenger_server_url = os.getenv("MESSENGER_SERVER_URL")
            self.messenger_server_name = os.getenv("MESSENGER_SERVER_NAME")

            self.messenger_admin_id = os.getenv("ADMIN_ID")
            self.messenger_admin_password = os.getenv("ADMIN_PASSWORD")
            self.messenger_admin_access_token = os.getenv("ADMIN_ACCESS_TOKEN")
            self.appservice_token = os.getenv("APP_SERVICE_TOKEN")
            self.homeserver_token = os.getenv("HOMESERVER")
            logger.info("Settings reloaded successfully.")
        except Exception as e:
            logger.exception(f"Failed to reload settings from environment variables: {e}")
            raise


    def generate_resident_json_list(self):
        try:
            _star = Star()
            resident_list = []
            # Iterate over resident directories
            for resident_id in os.listdir(_star.star_residents_data_home):
                resident_profile_full_path = os.path.join(_star.star_residents_data_home, resident_id, _star.resident_profile_subfolder)
                json_file_path = os.path.join(resident_profile_full_path, f"{resident_id}.json")
                if os.path.exists(json_file_path):
                    with open(os.path.join(resident_profile_full_path, f"{resident_id}.json"), 'r') as f:
                        resident_json = json.load(f)
                        resident_list.append(resident_json)

                if len(resident_list) > 0:
                    with open(_star.resident_list_json_path, 'w') as f:
                        json.dump(resident_list, f, indent=4)
                else:
                    with open(_star.resident_list_json_path, 'w') as file:
                        file.write("{}")  # Create an empty JSON file

            logger.info(f"Resident list successfully saved to {_star.resident_list_json_path}.")

        except Exception as e:
            logger.exception("Unexpected error in generate_resident_json_list.")


    def generate_group_json_list(self):
        try:
            _star = Star()
            group_list = []
            # Iterate over resident directories
            for group_id in os.listdir(_star.star_groups_data_home):
                group_profile_full_path = os.path.join(_star.star_groups_data_home, group_id, _star.group_profile_subfolder)
                json_file_path = os.path.join(group_profile_full_path, f"{group_id}.json")
                if os.path.exists(json_file_path):
                    with open(os.path.join(group_profile_full_path, f"{group_id}.json"), 'r') as f:
                        resident_json = json.load(f)
                        group_list.append(resident_json)

                if len(group_list) > 0:
                    with open(_star.resident_list_json_path, 'w') as f:
                        json.dump(group_list, f, indent=4)
                else:
                    with open(_star.resident_list_json_path, 'w') as file:
                        file.write("{}")  # Create an empty JSON file

            logger.info(f"Group list successfully saved to {_star.group_list_json_path}.")

        except Exception as e:
            logger.exception("Unexpected error in group_list_json_path.")
    

    # def update_setting(self, field_name: str, value: str):
    #     """Dynamically update a setting and reload it from the environment variables."""
        
    #     logger.info(f"Attempting to update setting: {field_name} with value: {value}")
        
    #     try:
    #         if hasattr(self, field_name):
    #             setattr(self, field_name, value)
    #             # utilities.update_env_file(field_name, value)
    #             # os.environ[field_name] = value  # Update the environment variable for this session
    #             logger.info(f"Setting '{field_name}' updated successfully to '{value}'.")
    #         else:
    #             logger.error(f"Field '{field_name}' does not exist in the settings.")
    #             raise ValueError(f"Field '{field_name}' does not exist in the settings.")
    #     except Exception as e:
    #         logger.exception(f"An error occurred while updating the setting '{field_name}': {e}")
    #         raise



# # Example usage:
# # Create a StarSettings instance
# settings = StarSettings()

# # Dynamically update a setting
# settings.update_setting('star_log_file_max_size', '10000000')

# # Reload the settings to get any external updates
# settings.reload_from_env()

# # Print the updated setting
# print(settings.star_log_file_max_size)

# def fetch_resident_data_paths_from_env():
#     try:
#         load_dotenv()
#         HOME_PATH_OF_DATA_OF_RESIDENTS = os.getenv("HOME_PATH_OF_DATA_OF_RESIDENTS")
#         RESIDENT_PROFILE_SUB_PATH = os.getenv("RESIDENT_PROFILE_SUB_PATH")
#         STAR_RESIDENT_LIST_JSON_PATH = os.getenv("STAR_RESIDENT_LIST_JSON_PATH")
        
#         return HOME_PATH_OF_DATA_OF_RESIDENTS, RESIDENT_PROFILE_SUB_PATH, STAR_RESIDENT_LIST_JSON_PATH
#     except Exception as e:
#         logger.exception(f"An error occurred in fetch_resident_data_paths_from_env: {e}")
#         raise

# def fetch_group_data_paths_from_env():
#     try:
#         load_dotenv()
#         HOME_PATH_OF_DATA_OF_GROUPS = os.getenv("HOME_PATH_OF_DATA_OF_GROUPS")
#         GROUP_PROFILE_SUB_PATH = os.getenv("GROUP_PROFILE_SUB_PATH")
#         STAR_GROUP_LIST_JSON_PATH = os.getenv("STAR_GROUP_LIST_JSON_PATH")
#         return HOME_PATH_OF_DATA_OF_GROUPS, GROUP_PROFILE_SUB_PATH, STAR_GROUP_LIST_JSON_PATH
#     except Exception as e:
#         logger.exception(f"An error occurred in fetch_group_data_paths_from_env: {e}")
#         raise

# async def sync_resident_settings():


# def generate_resident_json_list():
#     """
#     Generates a list of resident JSON data and saves it to a file.
#     Returns:
#         bool: True if successful, False otherwise.
#     """
#     try:
#         # Fetch data paths from environment
#         star_residents_data_home, resident_profile_subfolder, resident_list_json_path = fetch_resident_data_paths_from_env()
#         logger.debug("Fetched resident data paths from environment variables.")

#         resident_list = []

#         # Iterate over resident directories
#         for resident_id in os.listdir(star_residents_data_home):
#             resident_profile_full_path = os.path.join(star_residents_data_home, resident_id, resident_profile_subfolder)
#             if os.path.isdir(resident_profile_full_path) and resident_id.startswith("@"):
#                 try:
#                     with open(os.path.join(resident_profile_full_path, f"{resident_id}.json"), 'r') as f:
#                         resident_json = json.load(f)
#                         resident_list.append(resident_json)
#                         logger.debug(f"Added resident profile from {resident_profile_full_path}.")
#                 except json.JSONDecodeError as json_err:
#                     logger.error(f"JSON decode error in {resident_profile_full_path}: {json_err}")
#                     return False
#                 except Exception as file_err:
#                     logger.error(f"Error reading file {resident_profile_full_path}: {file_err}")
#                     return False

#         # Save the consolidated resident list
#         if resident_list:
#             try:
#                 with open(resident_list_json_path, 'w') as f:
#                     json.dump(resident_list, f, indent=4)
#                 logger.info(f"Resident list successfully saved to {resident_list_json_path}.")
#             except Exception as save_err:
#                 logger.error(f"Error saving resident list to {resident_list_json_path}: {save_err}")
#                 return False
#         else:
#             logger.warning("No resident profiles found to save.")
#             return False

#         return True
#     except Exception as e:
#         logger.exception("Unexpected error in generate_resident_json_list.")
#         return False


# def generate_group_json_list():
#     """
#     Generates a list of group JSON data and saves it to a file.
#     Returns:
#         bool: True if successful, False otherwise.
#     """
#     try:
#         # Fetch data paths from environment
#         star_groups_data_home, group_profile_subfolder, group_list_json_path = fetch_group_data_paths_from_env()
#         logger.debug("Fetched group data paths from environment variables.")

#         group_list = []

#         # Iterate over group directories
#         for group_id in os.listdir(star_groups_data_home):
#             group_profile_full_path = os.path.join(star_groups_data_home, group_id, group_profile_subfolder)
#             if os.path.isdir(group_profile_full_path) and group_id.startswith("!"):
#                 try:
#                     with open(os.path.join(group_profile_full_path, f"{group_id}.json"), 'r') as f:
#                         group_json = json.load(f)
#                         group_list.append(group_json)
#                         logger.debug(f"Added group profile from {group_profile_full_path}.")
#                 except json.JSONDecodeError as json_err:
#                     logger.error(f"JSON decode error in {group_profile_full_path}: {json_err}")
#                     return False
#                 except Exception as file_err:
#                     logger.error(f"Error reading file {group_profile_full_path}: {file_err}")
#                     return False

#         # Save the consolidated group list
#         if group_list:
#             try:
#                 with open(group_list_json_path, 'w') as f:
#                     json.dump(group_list, f, indent=4)
#                 logger.info(f"Group list successfully saved to {group_list_json_path}.")
#             except Exception as save_err:
#                 logger.error(f"Error saving group list to {group_list_json_path}: {save_err}")
#                 return False
#         else:
#             logger.warning("No group profiles found to save.")
#             return False

#         return True
#     except Exception as e:
#         logger.exception("Unexpected error in generate_group_json_list.")
#         return False


# def append_resident_json_list(resident_id) -> CrudStatus:
#     logger.info(f"Appending resident profile with ID: {resident_id} to the resident JSON list.")

#     try:
#         star_residents_data_home, resident_profile_subfolder, resident_list_json_path = fetch_resident_data_paths_from_env()

#         # Load the existing resident JSON list

#         try:
#             with open(resident_list_json_path, 'r') as f:
#                 resident_json_list = json.load(f)
#             logger.info(f"Successfully loaded existing resident JSON list from {resident_list_json_path}.")
#         except FileNotFoundError:
#             # If the file doesn't exist, initialize an empty list
#             logger.warning(f"Resident list file {resident_list_json_path} not found. Initializing an empty list.")
#             resident_json_list = []
#         except json.JSONDecodeError as e:
#             logger.error(f"Error decoding JSON from resident list file {resident_list_json_path}: {e}")
#             return CrudStatus.ERROR

#         # Read the resident's profile JSON data
#         resident_profile_path = os.path.join(star_residents_data_home, resident_id, resident_profile_subfolder, f"{resident_id}.json")
#         try:
#             with open(resident_profile_path, 'r') as f:
#                 resident_json = json.load(f)
#             logger.info(f"Successfully loaded resident profile from {resident_profile_path}.")
#         except FileNotFoundError:
#             logger.error(f"Resident profile file {resident_profile_path} not found.")
#             return CrudStatus.ERROR
#         except json.JSONDecodeError as e:
#             logger.error(f"Error decoding JSON from resident profile {resident_profile_path}: {e}")
#             return CrudStatus.ERROR

#         # Append the resident profile to the list
#         resident_json_list.append(resident_json)

#         # Write the updated list back to the JSON file
#         try:
#             with open(resident_list_json_path, 'w') as f:
#                 json.dump(resident_json_list, f, indent=4)  # Use json.dump to write properly formatted JSON
#             logger.info(f"Successfully updated resident list in {resident_list_json_path}.")
#         except IOError as e:
#             logger.error(f"Error writing to file {resident_list_json_path}: {e}")
#             return CrudStatus.ERROR

#         return CrudStatus.SUCCESS

#     except Exception as e:
#         logger.exception(f"An unexpected error occurred while appending resident profile: {e}")
#         return CrudStatus.EXCEPTION

# def append_group_json_list(group_id) -> CrudStatus:
#     logger.info(f"Appending group profile with ID: {group_id} to the group JSON list.")

#     try:
#         star_groups_data_home, group_profile_subfolder, group_list_json_path = fetch_group_data_paths_from_env()

#         # Load the existing group JSON list
#         try:
#             with open(group_list_json_path, 'r') as f:
#                 group_json_list = json.load(f)
#             logger.info(f"Successfully loaded existing group JSON list from {group_list_json_path}.")
#         except FileNotFoundError:
#             # If the file doesn't exist, initialize an empty list
#             logger.warning(f"Group list file {group_list_json_path} not found. Initializing an empty list.")
#             group_json_list = []
#         except json.JSONDecodeError as e:
#             logger.error(f"Error decoding JSON from group list file {group_list_json_path}: {e}")
#             return CrudStatus.ERROR

#         # Read the group's profile JSON data
#         group_profile_path = os.path.join(star_groups_data_home, group_id, group_profile_subfolder, f"{group_id}.json")
#         try:
#             with open(group_profile_path, 'r') as f:
#                 group_json = json.load(f)
#             logger.info(f"Successfully loaded group profile from {group_profile_path}.")
#         except FileNotFoundError:
#             logger.error(f"Group profile file {group_profile_path} not found.")
#             return CrudStatus.ERROR
#         except json.JSONDecodeError as e:
#             logger.error(f"Error decoding JSON from group profile {group_profile_path}: {e}")
#             return CrudStatus.ERROR

#         # Append the group profile to the list
#         group_json_list.append(group_json)

#         # Write the updated list back to the JSON file
#         try:
#             with open(group_list_json_path, 'w') as f:
#                 json.dump(group_json_list, f, indent=4)  # Use json.dump to write properly formatted JSON
#             logger.info(f"Successfully updated group list in {group_list_json_path}.")
#         except IOError as e:
#             logger.error(f"Error writing to file {group_list_json_path}: {e}")
#             return CrudStatus.ERROR

#         return CrudStatus.SUCCESS

#     except Exception as e:
#         logger.exception(f"An unexpected error occurred while appending group profile: {e}")
#         return CrudStatus.EXCEPTION

# find the corresponding element in msg_group.bihua_star.group_list_json_path based on resident_id, and replace, and save
# def update_resident_json_list(resident_id: str) -> CrudStatus:
#     try:
#         star_residents_data_home, resident_profile_subfolder, resident_list_json_path = fetch_resident_data_paths_from_env()
        
#         logger.info(f"Loading resident list from {resident_list_json_path}")
#         with open(resident_list_json_path, 'r') as f:
#             resident_json_list = json.load(f)
#     except FileNotFoundError:
#         logger.error(f"Resident list file {resident_list_json_path} not found.")
#         return CrudStatus.ERROR
#     except json.JSONDecodeError:
#         logger.error(f"Error decoding JSON from resident list file {resident_list_json_path}.")
#         return CrudStatus.ERROR

#     try:
#         logger.info(f"Loading updated resident profile for ID {resident_id}")
#         updated_resident_profile_json_path = os.path.join(star_residents_data_home, resident_id, resident_profile_subfolder, f"{resident_id}.json")
        
#         if not updated_resident_profile_json_path:
#             logger.error(f"Resident with ID {resident_id} not found.")
#             return CrudStatus.ERROR
#         with open(os.path.join(updated_resident_profile_json_path, f"{resident_id}.json"), 'r') as f:
#                         updated_resident_json = json.load(f)
#     except Exception as e:
#         logger.exception(f"Unexpected error occurred while processing resident data: {e}")
#         return CrudStatus.EXCEPTION

#     for i, resident_json in enumerate(resident_json_list):
#         if resident_json.get('resident_id') == resident_id:
#             logger.info(f"Updating resident profile for ID {resident_id}")
#             resident_json_list[i] = updated_resident_json
#             break
#     else:
#         logger.warning(f"Resident with ID {resident_id} not found in the list.")
#         return CrudStatus.ERROR

#     try:
#         logger.info(f"Saving updated resident list to {resident_list_json_path}")
#         with open(resident_list_json_path, 'w') as f:
#             json.dump(resident_json_list, f, indent=4)
#     except IOError as e:
#         logger.error(f"Error writing to resident list file {resident_list_json_path}: {e}")
#         return CrudStatus.ERROR

#     logger.info(f"Resident profile for ID {resident_id} updated successfully.")
#     return CrudStatus.SUCCESS

# def update_group_json_list(group_id: str) -> CrudStatus:
#     try:
#         star_groups_data_home, group_profile_subfolder, group_list_json_path = fetch_group_data_paths_from_env()
        
#         logger.info(f"Loading group list from {group_list_json_path}")
#         with open(group_list_json_path, 'r') as f:
#             group_json_list = json.load(f)
#     except FileNotFoundError:
#         logger.error(f"Group list file {group_list_json_path} not found.")
#         return CrudStatus.ERROR
#     except json.JSONDecodeError:
#         logger.error(f"Error decoding JSON from group list file {group_list_json_path}.")
#         return CrudStatus.EXCEPTION

#     try:
#         logger.info(f"Loading updated group profile for ID {group_id}")
#         updated_group_json_path = os.path.join(star_groups_data_home, group_id, group_profile_subfolder, f"{group_id}.json")
#         with open(updated_group_json_path, 'r') as f:
#             updated_group_json = json.load(f)
#         if not updated_group_json:
#             logger.warning(f"Group with ID {group_id} not found.")
#             return CrudStatus.EXCEPTION
#     except Exception as e:
#         logger.exception(f"Unexpected error occurred while processing group data: {e}")
#         return CrudStatus.ERROR

#     for i, group_json in enumerate(group_json_list):
#         if group_json.get('group_id') == group_id:
#             logger.info(f"Updating group profile for ID {group_id}")
#             group_json_list[i] = updated_group_json
#             break
#     else:
#         logger.warning(f"Group with ID {group_id} not found in the list.")
#         return CrudStatus.ERROR

#     try:
#         logger.info(f"Saving updated group list to {group_list_json_path}")
#         with open(group_list_json_path, 'w') as f:
#             json.dump(group_json_list, f, indent=4)
#     except IOError as e:
#         logger.error(f"Error writing to group list file {group_list_json_path}: {e}")
#         return CrudStatus.EXCEPTION

#     logger.info(f"Group profile for ID {group_id} updated successfully.")
#     return CrudStatus.SUCCESS


# print("start...")
# _star = Star()
# _star.update_setting("messenger_admin_access_token", "test")
# print(_star.messenger_admin_access_token)




