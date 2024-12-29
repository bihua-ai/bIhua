import asyncio
import importlib
import importlib.util
import aiohttp
import os
import requests
import datetime as dt

from nio import AsyncClient, MatrixRoom, Event, JoinResponse, JoinError
from bihua.configuration_manager import ConfigManager
from bihua.bihua_star import Star
from bihua_logging import get_logger
from status_definitions import RegisterStatus, AgentStatus
import star_resident
from star_resident import Resident
import utilities
from bihua.configuration_manager import config_manager

# config_manager.get_config_loader().load_env() # load .env file, not really needed. Just for readability

logger = get_logger()

class EventWrapper:
    def __init__(self, room, event):
        self.event = event
        self.group = room

class BihuaAgentService:
    # example, bihua_agent_service_config_location = /path/to/custom/config
    def __init__(self, bihua_agent_service_config_location = None):
        """
        Initialize the BihuaAppservice.

        :param homeserver_URL: The Matrix homeserver URL
        """
        logger.info("Initializing BihuaAgentService...")
        self.star = Star()
        self.homeserver_URL = self.star.messenger_server_url
        self.password = self.star.messenger_admin_password
        self.agent_ids = []
        # self.current_client = None
        self.current_agent_id = None

        self.clients = {}  # Store clients for each agent
        # self.client_access_tokens = {}  # Store access tokens for each agent
        self.message_handlers = {}  # Store custom handlers for each agent
        logger.info(f"BihuaAgentService initialized with homeserver: {self.homeserver_URL}")

    # Full name of caklback function is on_message_received_{agent_id}, e.g., on_message_received_bot_001
    # agent_id is also agent file name, agent_001.py
    # agent_file_path is the full path of the agent file, e.g., /opt/bihua_cient/agents/bot_001.py
    def import_handler(self, agent_name, agent_file_path, agent_callback_name="on_message_received"):
        """Dynamically import the handler for the agent."""
        logger.info(f"Importing handler for {agent_name} from {agent_file_path}...")
        try:
            # Load the module from the given file path
            spec = importlib.util.spec_from_file_location(agent_name, agent_file_path)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load module spec for {agent_name} from {agent_file_path}.")
                return None

            agent_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(agent_module)

            # Construct the handler function name dynamically
            callback_function_name = f"{agent_callback_name}_{agent_name}"

            # Dynamically get the handler function from the module
            handler = getattr(agent_module, callback_function_name, None)
            if handler is None:
                logger.error(f"Handler function '{callback_function_name}' not found in the module '{agent_name}'.")
                return None

            logger.info(f"Handler function '{callback_function_name}' successfully loaded for {agent_name}.")
            return handler
        except Exception as e:
            logger.error(f"Error importing handler for {agent_name}: {e}")
            return None


        #     module = importlib.import_module(f"agents.{agent_id}")
        #     handler = getattr(module, f"{event_callbackname}_{agent_id}")
        #     logger.info(f"Handler {handler} for {agent_id} imported successfully.")
        #     return handler
        # except (ModuleNotFoundError, AttributeError) as e:
        #     logger.error(f"Error importing handler for {agent_id}: {e}")
        #     # return None
        # handler_name = extract_handler_name(script_path)
    
        # spec = importlib.util.spec_from_file_location(handler_name, script_path)
        # print(f"Module spec: {spec}")
        # agent_module = importlib.util.module_from_spec(spec)
        # print(f"Agent module: {agent_module}")
        # spec.loader.exec_module(agent_module)

        # # Construct the handler function name dynamically
        # callback_function_name = f"on_message_received_{handler_name}"
        # # Dynamically get the handler function from the module
        # handler = getattr(agent_module, callback_function_name, None)
        # if handler is None:
        #     print(f"Handler function '{callback_function_name}' not found in the module.")
        # return handler

    async def add_agent(self, username, agent_id, agent_dir_path):
        """Create a bot and assign a custom message handler to it."""
        try:
            logger.info(f"Adding agent {username}...")
            agent_id = f"@{username}:{utilities.extract_homeserver_name(self.homeserver_URL)}"
            _registerStatus = await star_resident.register_user(username, self.password, self.homeserver_URL)
            if _registerStatus not in {RegisterStatus.SUCCESS, RegisterStatus.USER_EXISTS}:
                logger.error(f"Error registering agent {username}: {_registerStatus}")
                return
            # client = AsyncClient(self.homeserver_URL, agent_id)
            # self.clients[agent_id] = client

            # response = await client.login(self.password)
            # self.client_access_tokens[agent_id] = client.access_token
            # await client.logout()
            # await client.close()
            self.agent_ids.append(agent_id)
            agent_name, servername = utilities.split_resident_id(agent_id)
            agent_file_full_path = os.path.join(agent_dir_path, f"{agent_name}.py")
            handler = self.import_handler(agent_name, agent_file_full_path)
            self.message_handlers[agent_id] = handler
            if handler:
                self.message_handlers[agent_id] = handler
            logger.info(f"Agent {username} added with ID {agent_id}")
        except Exception as e:
            logger.error(f"Error adding agent {username}: {e}")

    async def setup_agents(self, agent_dir_path):
        """Scan the 'agents' directory and create bots for each agent."""
        logger.info(f"Setting up agents from {agent_dir_path}...")
        agent_files = [
            f[:-3]
            for f in os.listdir(agent_dir_path)
            if f.endswith(".py") and f != "__init__.py"
        ]
        logger.info(f"Found agents: {agent_files}")
        for agent in agent_files:
            await self.add_agent(agent, agent, agent_dir_path)

    async def set_group(self, group_alias, group_topic):
        logger.info(f"Setting up group with alias {group_alias} and topic {group_topic}...")
        encoded_group_alias = utilities.encode_group_alias(group_alias)
        check_url = f"{self.homeserver_URL}/_matrix/client/r0/directory/room/{encoded_group_alias}"
        headers = {
            "Authorization": f"Bearer {self.star.messenger_admin_access_token}",
            "Content-Type": "application/json",
        }

        if "#" in group_alias:
            group_name = group_alias.split(":")[0][1:]
        else:
            group_name = group_alias

        async with aiohttp.ClientSession() as session:
            # Check if the group already exists
            async with session.get(check_url, headers=headers) as check_response:
                if check_response.status == 200:
                    logger.info(f"Group with alias '{group_alias}' already exists.")
                    return {"status": "exists", "message": f"Group with alias '{group_alias}' already exists."}
                elif check_response.status != 404:
                    logger.error(f"Error checking group existence: {check_response.status} - {await check_response.text()}")
                    return {"status": "error", "message": f"Error checking group: {check_response.status}"}

            # Create a new group if it doesn't exist
            url = f"{self.homeserver_URL}/_matrix/client/r0/createRoom"
            data = {
                "preset": "public_chat",
                "name": group_name,
                "topic": group_topic,
                "visibility": "public",
                "creation_content": {
                    "m.federate": True
                },
                "room_alias_name": group_name
            }

            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    logger.info(f"Group '{group_name}' created successfully.")
                    return {"status": "created", "message": f"Group '{group_name}' created successfully."}
                else:
                    logger.error(f"Error creating group: {response.status} - {await response.text()}")
                    return {"status": "error", "message": f"Error creating group: {response.status}"}

    async def join_group(self, group_id=None, group_alias=None):
        logger.info(f"Joining group with ID: {group_id} or alias: {group_alias}...")
        if not group_id and not group_alias:
            logger.error("Error: No group ID or alias provided.")
            return
        
        # Resolve the group alias to get the room ID
        if group_alias:
            encoded_group_alias = utilities.encode_group_alias(group_alias)
            resolve_url = f"{self.homeserver_URL}/_matrix/client/r0/directory/room/{encoded_group_alias}"
            headers = {
                "Authorization": f"Bearer {self.star.messenger_admin_access_token}",
                "Content-Type": "application/json",
            }
            resolve_response = requests.get(resolve_url, headers=headers)
            if resolve_response.status_code == 200:
                group_id = resolve_response.json().get("room_id")
                logger.info(f"Resolved room alias {group_alias} to room ID: {group_id}")
            else:
                logger.error(f"Error resolving room alias {group_alias}: {resolve_response.status_code} - {resolve_response.text}")
                return

        if not group_id:
            logger.error("Error: No valid room ID to join.")
            return

        for agent_id in self.agent_ids:
            # access_token = self.client_access_tokens[agent_id]
            # Check if the agent is already in the room
            check_membership_url = f"{self.homeserver_URL}/_matrix/client/r0/rooms/{group_id}/joined_members"
            check_membership_response = requests.get(check_membership_url, headers={
                "Authorization": f"Bearer {self.star.messenger_admin_access_token}",
                "Content-Type": "application/json",
            })
            
            if check_membership_response.status_code == 200:
                joined_members = check_membership_response.json().get("joined", {})
                if agent_id in joined_members:
                    logger.info(f"User {agent_id} is currently joined in the room.")
                    continue
                else:
                    logger.info(f"User {agent_id} is NOT currently joined in the room.")
                    client = AsyncClient(self.homeserver_URL, agent_id)
                    await client.login(self.password)
                    response = await client.join(group_alias)
                    if isinstance(response, JoinError):
                        logger.error(f"Failed to join room: {response.message}")
                    else:
                        logger.info(f"Successfully joined the room: {group_alias}")
                    
                    client.logout()
                    client.close()

            else:
                logger.error(f"Error checking membership for agent {agent_id}: {check_membership_response.status_code} - {check_membership_response.text}")
    
    # async def message_callback(self, room: MatrixRoom, event: Event):
    #     """Callback function to handle messages."""
    #     # Wrap the dynamically loaded callback for compatibility
    #     class EventWrapper:
    #         def __init__(self, room, event):
    #             self.event = event
    #             self.room = room

    #     handler = self.message_handlers.get(self.current_agent_id)
    #     client = self.clients.get(self.current_agent_id)
    #     event_wrapper = EventWrapper(room, event)
        
    #     if handler:
    #         print(f"Handler found for {self.current_agent_id} {handler} {client}.")
    #         await handler(event_wrapper, client)
    #     else:
    #         print("No handler found.")

    async def start_one_agent(self, homeserver, agent_id, password, agent_script_full_path):
        logger.info(f"Starting agent {agent_id}...")
        
        try:
            _resident = Resident(agent_id)
            client = AsyncClient(homeserver, agent_id)
            self.clients[agent_id] = client
            
            # Create a unique message callback for this agent
            async def agent_message_callback(room: MatrixRoom, event: Event):
                """Callback function for this specific agent."""
                # Wrap the dynamically loaded callback for compatibility

                # Add message saving mechanism here
                print(f"Message received by {agent_id}, from {event.sender}: {event.body}")

                # class EventWrapper:
                #     def __init__(self, room, event):
                #         self.event = event
                #         self.group = room

                handler = self.message_handlers.get(agent_id)  # Use agent_id directly
                event_wrapper = EventWrapper(room, event)
                
                if handler:
                    print(f"Handler found for {agent_id}: {handler}.")
                    await handler(event_wrapper, client)
                else:
                    print(f"No handler found for {agent_id}.")

            # Register the unique callback
            client.add_event_callback(agent_message_callback, Event)

            # Log in the client and start syncing
            await client.login(password)
            last_login_timestamp_ms = dt.datetime.timestamp(dt.datetime.now()) * 1000
            _resident.resident_settings_update(last_login_timestamp_ms=last_login_timestamp_ms)
            logger.info(f"Agent {agent_id} is now running.")
            await client.sync_forever(timeout=3000)
        except Exception as e:
            logger.error(f"start_one_agent.start error for {agent_id}: {e}")


    async def start_all_agents(self, agent_dir_path):

        logger.info("Starting all agents...")
        _star = Star()
        agent_json_list = star_resident.get_all_residents_from_messenger(_star.messenger_server_url, _star.messenger_admin_access_token)

        try:
            coroutines = []
            count = 0
            for agent_element in agent_json_list:
                
                s = agent_element["deactivated"]
                logger.info(f"Processing agent {count}...")

                # debug here
                state = agent_element["deactivated"]
                print(f"STATE = {state}")
                if agent_element["deactivated"] == False: # agent_element["name"] is an agent_id
                    if agent_element["name"] not in self.agent_ids:
                        logger.info(f"Agent {agent_element['name']} is not in the list, skipping.")
                    else:
                        count = count + 1
                        agent_script_full_path = agent_dir_path + agent_element["name"] + ".py"
                        self.current_agent_id = agent_element["name"]
                        print(f"agent in start_all_agent = {self.current_agent_id}")
                        job = asyncio.create_task(self.start_one_agent(_star.messenger_server_url, agent_element["name"], _star.messenger_admin_password, agent_script_full_path) ) # agent_script_full_path = "/opt/bihua_cient/agents/bot_001.py"
                        coroutines.append(job)
            futures = await asyncio.gather(*coroutines, return_exceptions=True)
            # Handle results

            print(f"Number of tasks = {count}")
            # for i, result in enumerate(futures):
            #     if isinstance(result, Exception):
            #         logger.error(f"Task {i + 1} failed with exception: {result}")
            #     else:
            #         logger.info(f"Task {i + 1} completed successfully: {result}")
        except Exception as e:
            logger.error(f"Error starting all agents: {e}")

    async def agent_group_runner(self, group_alias, group_topic, agent_dir_path):
        try:
            logger.info(f"Running agent group with alias {group_alias} and topic {group_topic}...")
            await self.set_group(group_alias, group_topic)
            await self.setup_agents(agent_dir_path)
            
            # print(f"self.clients = {self.clients}")
            # print(f"agent_ids={agent_ids}")
            await self.join_group(group_alias=group_alias)
            await self.start_all_agents(agent_dir_path)
        except Exception as e:
            logger.error(f"Error running agent group: {e}")
