import os
import importlib
import asyncio, json, requests
from nio import AsyncClient, AsyncClientConfig, MatrixRoom, RoomMessageText
from aiohttp import web
from bihua_one_star import Star
from bihua_logging import get_logger

logger = get_logger()

# Best way to run clients is on the same machine of homeserver
# Although we can run clients on different machines, but it is not recommended, because agent data is stored in client machine.

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
        self.message_handlers = {}  # Store custom handlers for each agent

    async def create_agent(self, username, on_message_received): # username is the agent name
        """Create a bot and assign a custom message handler to it."""
        agent_id = f"@{username}:{self.homeserver_URL}"
        client = AsyncClient(self.homeserver_URL, agent_id)
        self.clients[agent_id] = client
        
        # Dynamically import the handler for the bot
        handler = self.import_handler(on_message_received)
        if handler:
            self.message_handlers[agent_id] = handler

    async def create_group(self, group_alias, group_topic):
        # The Matrix API endpoint to create a room (group)
        url = f"{self.homeserver_URL}/_matrix/client/r0/createRoom"
        
        headers = {
            "Authorization": f"Bearer {self.as_token}",
            "Content-Type": "application/json"
        }
        if "#" in group_alias:
            group_name = group_alias.split(":")[0][1:]
        else:
            group_name = group_alias

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
        
        if response.status_code != 200:
            logger.error(f"Error creating group: {response.status_code} - {response.text}")


    # async def join_group(self, room_id, agents):
    #     if not room_id:
    #         logger.error("Error: No group to join.")
    #         return

    #     # Join each agent to the room
    #     for agent in agents:
    #         logger.info(f"Agent {agent} joining group {room_id}")
            
    #         # Matrix API to join a room (group)
    #         url = f"{self.homeserver_URL}/_matrix/client/r0/join/{room_id}"
    #         headers = {
    #             "Authorization": f"Bearer {self.as_token}",
    #             "Content-Type": "application/json"
    #         }

    #         # Send request for the agent to join the room
    #         response = requests.post(url, headers=headers)
    #         if response.status_code == 200:
    #             logger.info(f"Agent {agent} joined the group successfully.")
    #         else:
    #             logger.error(f"Error joining group for agent {agent}: {response.status_code} - {response.text}")

    def import_handler(self, on_message_received):
        """Dynamically import the handler for the agent."""
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

    async def start(self):
        """Start the appservice."""
        app = web.Application()
        app.router.add_post("/transactions", self.handle_transactions)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "localhost", 9000)
        await site.start()

    async def handle_transactions(self, request):
        """Handle incoming transactions from the homeserver."""
        data = await request.json()
        for event in data.get("events", []):
            await self.on_event(event)
        return web.Response()

    # Automatically scan the 'agents' directory and create bots for each agent
    async def setup_agents(self, agent_dir_path):
      # Scan the given directory for Python files (excluding __init__.py)
        agent_files = [
            f[:-3] for f in os.listdir(agent_dir_path)  # Remove '.py' extension, agent_001.py -> agent_001
            if f.endswith(".py") and f != "__init__.py"
        ]
        
        # Create bots dynamically for each agent file found
        for agent in agent_files:
            await self.create_agent(agent, agent) # agent_001.py -> custom_message_handler_agent_001
                                                  # username, on_message_received



# if __name__ == "__main__":
#     appservice = asyncio.run(setup_agents())
#     asyncio.run(appservice.start())
