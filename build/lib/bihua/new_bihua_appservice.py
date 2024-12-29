import os
import importlib
import asyncio, json, requests
from nio import AsyncClient, AsyncClientConfig, MatrixRoom, RoomMessageText
from aiohttp import web
from bihua_one_star import Star
from bihua_logging import get_logger
import signal
import requests
import json

logger = get_logger()

# Best way to run clients is on the same machine of homeserver
# Although we can run clients on different machines, but it is not recommended, because agent data is stored in client machine.

def is_appservice_registered(homeserver_url, homeserver_token, appservice_id):
    """
    Checks if the application service is already registered with the homeserver.
    
    :param homeserver_url: The base URL of the Matrix homeserver (e.g., 'http://localhost:8008')
    :param homeserver_token: The homeserver token used for authentication (as configured in homeserver.yaml)
    :param appservice_id: The ID of the application service to check for
    :return: True if the appservice is registered, False otherwise
    """
    check_url = f"{homeserver_url}/_synapse/admin/v1/appservice/{appservice_id}"
    
    headers = {
        'Authorization': f'Bearer {homeserver_token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(check_url, headers=headers)
    
    if response.status_code == 200:
        print(f"Application service '{appservice_id}' is already registered.")
        return True
    elif response.status_code == 404:
        print(f"Application service '{appservice_id}' is not registered.")
        return False
    else:
        print(f"Error checking application service: {response.status_code}")
        print(response.text)
        return False

class BihuaAppservice:
    def __init__(self, homeserver_URL=None):
        """
        Initialize the BihuaAppservice.

        :param homeserver: The Matrix homeserver URL
        :param as_token: The appservice token
        :param hs_token: The homeserver token
        """

        self.star = Star()

        # Force caller to supply server URL, so caller knows it is the server he wants to connect to
        self.homeserver_URL = self.star.messenger_server_url
        self.as_token = self.star.appservice_token
        self.hs_token = self.star.homeserver_token
        self.clients = {} # Store clients for each agent
        self.message_handlers = {}  # Store custom handlers for each 

    def register_appservice(self, homeserver_url, appservice_token, homeserver_token):
        """
        Registers an application service with the homeserver, but only if it's not already registered.

        :param homeserver_url: The base URL of the Matrix homeserver (e.g., 'http://localhost:8008')
        :param appservice_token: The appservice token for authenticating the appservice
        :param homeserver_token: The homeserver token for authenticating the request
        """
        appservice_id = "bihua_agent_appservice"

        # First, check if the appservice is already registered
        if is_appservice_registered(homeserver_url, homeserver_token, appservice_id):
            print(f"Skipping registration. '{appservice_id}' is already registered.")
            return

        # Define the registration URL
        register_url = f"{homeserver_url}/_synapse/admin/v1/register"

        # Define the appservice configuration payload
        payload = {
            "id": appservice_id,
            "url": "http://localhost:9000",  # The appservice's own listener
            "as_token": appservice_token,
            "hs_token": homeserver_token,
            "rate_limited": False,
            "sender_localpart": "bihua_agent",
            "namespaces": {
                "users": [{
                    "exclusive": True,
                    "regex": "@agent_.*:messenger.b1.shuwantech.com"
                }],
                "rooms": [{
                    "exclusive": False,
                    "regex": ".*"
                }],
                "aliases": [{
                    "exclusive": False,
                    "regex": "#group_.*:messenger.b1.shuwantech.com"
                }]
            }
        }

        # Define the headers for the request
        headers = {
            'Authorization': f'Bearer {homeserver_token}',  # Use homeserver token for authentication
            'Content-Type': 'application/json'
        }

        # Send the request to register the application service
        response = requests.post(register_url, headers=headers, json=payload)

        # Check the response status
        if response.status_code == 200:
            print("Application service registered successfully!")
            return response.json()  # Optionally return the response data
        else:
            print("Failed to register application service.")
            print(f"Status Code: {response.status_code}")
            print(f"Error Message: {response.text}")
            return None

    async def create_agent(self, username, on_message_received): # username is the agent name
        """Create a bot and assign a custom message handler to it."""
        agent_id = f"@{username}:{self.homeserver_URL.replace('https://', '').replace('http://', '')}"
        # agent_id = f"@{username}:{self.homeserver_URL}"
        logger.info(f"Creating agent: {agent_id}")
        try:
            client = AsyncClient(self.homeserver_URL, agent_id)
            self.clients[agent_id] = client
            logger.info(f"Agent client created and added to clients dictionary: {agent_id}")
            
            # Dynamically import the handler for the bot
            handler = self.import_handler(on_message_received)
            if handler:
                self.message_handlers[agent_id] = handler

            return agent_id
        except Exception as e:
            logger.error(f"Error creating agent {agent_id}: {e}")
            raise

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


    def import_handler(self, on_message_received):
        """Dynamically import the handler for the agent."""
        logger.info(f"Importing handler for {on_message_received}")
        try:
            # Import the handler function from the specified module
            module = importlib.import_module(f"agents.{on_message_received}")
            handler = getattr(module, f"custom_message_handler_{on_message_received}")
            return handler
        except (ModuleNotFoundError, AttributeError) as e:
            logger.error(f"Error importing handler for {on_message_received}: {e}")
            return None

    async def on_event(self, event):
        """Handle events from the Matrix server."""
        logger.info(f"Event received: {event}")
        if event.type == "m.room.message":
            sender = event.sender
            room_id = event.room_id  # Room ID where the message came from
            body = event.body
            logger.info(f"Message from {sender} in room {room_id}: {body}")

            # Check if the sender has a custom message handler
            if sender in self.message_handlers:
                custom_handler = self.message_handlers[sender]
                # Call the custom message handler for this sender
                if custom_handler:
                    await custom_handler(event, self.clients[sender])
            else:
                logger.info(f"No custom handler found for {sender}, using default.")

    async def send_message(self, room_id, message):
        """Send a message to the specified room."""
        message_event = RoomMessageText(body=message)
        await self.clients[list(self.clients.keys())[0]].send_message(room_id, message_event)
        logger.info(f"Message sent to room {room_id}: {message}")

    # async def start(self):
    #     """Start the appservice."""
    #     app = web.Application()
    #     app.router.add_post("/transactions", self.handle_transactions)
    #     runner = web.AppRunner(app)
    #     await runner.setup()
    #     site = web.TCPSite(runner, "localhost", 9000)
    #     await site.start()
    # async def start(self):
    #     loop = asyncio.get_event_loop()

    #     # Define a synchronous wrapper for the coroutine
    #     def shutdown_wrapper():
    #         asyncio.create_task(self.graceful_shutdown(site))

    #     loop.add_signal_handler(signal.SIGINT, shutdown_wrapper)

    #     # Example setup logic
    #     print("Appservice is listening on http://localhost:9000")
    #     await asyncio.Future()  # Replace with your actual server code

    async def start(self):
        """Start the appservice."""
        app = web.Application()
        app.router.add_post("/transactions", self.handle_transactions)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", 9000)
        await site.start()

        # Add a log to confirm the appservice is running
        logger.info("Appservice is listening on http://localhost:9000")

        # Gracefully handle shutdown signals
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(self.graceful_shutdown(site)))
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self.graceful_shutdown(site)))

    #     # Keep the event loop running indefinitely
        await asyncio.Future()  # Block forever until a shutdown signal is received

    async def graceful_shutdown(self, site):
        """Gracefully shutdown the web server."""
        logger.info("Received shutdown signal. Shutting down server...")
        await site.stop()
        logger.info("Server stopped. Exiting...")

    async def handle_transactions(self, request):
        """Handle incoming transactions from the homeserver."""
        data = await request.json()
        for event in data.get("events", []):
            await self.on_event(event)
        return web.Response()

    # Automatically scan the 'agents' directory and create bots for each agent
    async def setup_agents(self, agent_dir_path):
        """Automatically scan the 'agents' directory and create bots for each agent."""
        
        # Scan the given directory for Python files (excluding __init__.py)
        agent_files = [
            f[:-3] for f in os.listdir(agent_dir_path)  # Remove '.py' extension, agent_001.py -> agent_001
            if f.endswith(".py") and f != "__init__.py"
        ]
        
        # Initialize an empty list to hold the agent IDs
        agent_ids = []
        
        # Create bots dynamically for each agent file found
        for agent in agent_files:
            agent_id = f"@{agent}:{self.homeserver_URL.replace('https://', '').replace('http://', '')}"
            print(agent_id)
            await self.create_agent(agent, agent)  # Create the agent and assign the handler
            agent_ids.append(agent_id)  # Add the agent ID to the list
        
        # Return the list of agent IDs
        return agent_ids


# if __name__ == "__main__":
#     appservice = asyncio.run(setup_agents())
#     asyncio.run(appservice.start())
