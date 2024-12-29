import asyncio
import importlib
import aiohttp
import os
import requests
import datetime as dt

from nio import AsyncClient, MatrixRoom, Event, JoinResponse, JoinError
from bihua_one_star import Star
from bihua_logging import get_logger
from status_definitions import RegisterStatus, AgentStatus
import messenger_resident
from messenger_resident import Resident
import utilities

logger = get_logger()

class BihuaAgentService:
    def __init__(self, homeserver_URL=None):
        """
        Initialize the BihuaAppservice.

        :param homeserver_URL: The Matrix homeserver URL
        """
        logger.info("Initializing BihuaAgentService...")
        self.star = Star()
        self.homeserver_URL = homeserver_URL or self.star.messenger_server_url
        self.password = self.star.messenger_admin_password
        self.clients = {}  # Store clients for each agent
        self.client_access_tokens = {}  # Store access tokens for each agent
        self.message_handlers = {}  # Store custom handlers for each agent
        logger.info(f"BihuaAgentService initialized with homeserver: {self.homeserver_URL}")

    def import_handler(self, on_message_received):
        """Dynamically import the handler for the agent."""
        try:
            logger.info(f"Importing handler for {on_message_received}...")
            module = importlib.import_module(f"agents.{on_message_received}")
            handler = getattr(module, f"on_message_received_{on_message_received}")
            logger.info(f"Handler {handler} for {on_message_received} imported successfully.")
            return handler
        except (ModuleNotFoundError, AttributeError) as e:
            logger.error(f"Error importing handler for {on_message_received}: {e}")
            return None

    async def add_agent(self, username, on_message_received):
        """Create a bot and assign a custom message handler to it."""
        try:
            logger.info(f"Adding agent {username}...")
            agent_id = f"@{username}:{utilities.extract_homeserver_name(self.homeserver_URL)}"
            _registerStatus = await messenger_resident.register_user(username, self.password, self.homeserver_URL)
            if _registerStatus not in {RegisterStatus.SUCCESS, RegisterStatus.USER_EXISTS}:
                logger.error(f"Error registering agent {username}: {_registerStatus}")
                return
            client = AsyncClient(self.homeserver_URL, agent_id)
            self.clients[agent_id] = client

            response = await client.login(self.password)
            self.client_access_tokens[agent_id] = client.access_token
            await client.logout()
            await client.close()

            handler = self.import_handler(on_message_received)
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
            await self.add_agent(agent, agent)

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

    async def join_group(self, group_id=None, group_alias=None, agent_ids=None):
        logger.info(f"Joining group with ID: {group_id} or alias: {group_alias}...")
        agent_ids = agent_ids or list(self.clients.keys())
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

        for agent_id in agent_ids:
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



                    # Proceed to join the group if not already a member
                    # url = f"{self.homeserver_URL}/_matrix/client/r0/join/{group_id}"
                    # print(f"***access_token = {access_token}")
                    # url = f"{self.homeserver_URL}/_matrix/client/r0/rooms/{group_id}/join"
                    # headers = {
                    #     "Authorization": f"Bearer {access_token}",
                    #     "Content-Type": "application/json",
                    # }
                    # response = requests.post(url, headers=headers)

                    # if response.status_code == 200:
                    #     logger.info(f"Agent {agent_id} successfully joined group with room ID {group_id}.")
                    # else:
                    #     logger.error(f"Error joining group for agent {agent_id}: {response.status_code} - {response.text}")
            # else:
            #     logger.error(f"Error checking membership for agent {agent_id}: {check_membership_response.status_code} - {check_membership_response.text}")


    async def start_one_agent(self, homeserver, agent_id, password):
        logger.info(f"Starting agent {agent_id}...")
        _resident = Resident(agent_id)

        try:
            if agent_id in self.message_handlers:
                callback_function = self.message_handlers[agent_id]
                print(f"callback_function = {callback_function}")

                # Ensure the callback function matches the required signature
                async def event_callback(room: MatrixRoom, event: Event):
                    await callback_function(room, event)

                # Add the dynamically created event callback
                self.clients[agent_id].add_event_callback(event_callback, Event)
            else:
                logger.error(f"No handler defined for agent {agent_id}.")

            await self.clients[agent_id].login(password)
            
            laslogin_timestamp_ms = dt.datetime.timestamp(dt.datetime.now()) * 1000
            _resident.resident_settings_update(last_login_timestamp_ms=laslogin_timestamp_ms)

            await self.clients[agent_id].sync_forever()
            logger.info(f"Agent {agent_id} is now running.")
        except Exception as e:
            logger.error(f"start_one_agent.start error for {agent_id}: {e}")

    async def start_all_agents(self):
        logger.info("Starting all agents...")
        _star = Star()
        agent_json_list = messenger_resident.get_all_residents_from_messenger(_star.messenger_server_url, _star.messenger_admin_access_token)

        agent_ids = self.clients.keys()

        try:
            coroutines = []
            count = 0
            for agent_element in agent_json_list:
                count = count + 1
                s = agent_element["deactivated"]
                logger.info(f"Processing agent {count}...")

                # debug here

                if agent_element["deactivated"] == False:
                    if agent_element["name"] not in agent_ids:
                        logger.info(f"Agent {agent_element['name']} is not in the list, skipping.")
                        continue
                    job = asyncio.create_task(self.start_one_agent(_star.messenger_server_url, agent_element["name"], _star.messenger_admin_password))
                    coroutines.append(job)
            futures = await asyncio.gather(*coroutines, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error starting all agents: {e}")

    async def agent_group_runner(self, group_alias, group_topic, agent_dir_path):
        try:
            logger.info(f"Running agent group with alias {group_alias} and topic {group_topic}...")
            await self.set_group(group_alias, group_topic)
            await self.setup_agents(agent_dir_path)
            agent_ids=list(self.clients.keys())
            # print(f"self.clients = {self.clients}")
            # print(f"agent_ids={agent_ids}")
            await self.join_group(group_alias=group_alias, agent_ids=list(self.clients.keys()))
            await self.start_all_agents()
        except Exception as e:
            logger.error(f"Error running agent group: {e}")
