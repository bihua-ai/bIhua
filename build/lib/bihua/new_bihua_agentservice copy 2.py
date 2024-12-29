import os
import importlib
import asyncio
import json
import requests
from nio import AsyncClient, AsyncClientConfig, MatrixRoom, RoomMessageText
from aiohttp import web
from bihua_one_star import Star
from bihua_logging import get_logger
import messenger_resident
from messenger_resident import Resident

from dotenv import load_dotenv
from typing import List
from pydantic import BaseModel
import datetime as dt
import time

logger = get_logger()

# Docker Commands
# sudo docker build --no-cache -t bihua-python:latest -f Dockerfile_python .
# sudo docker run -p 8300:8000 --name bihua-python bihua-python:latest
# sudo docker ps -a
# sudo docker rm <docker-id>
# digitalorganism / May221996

class BihuaAgentService:
    def __init__(self, homeserver_URL=None):
        """
        Initialize the BihuaAppservice.

        :param homeserver_URL: The Matrix homeserver URL
        """
        self.star = Star()
        self.homeserver_URL = self.star.messenger_server_url
        self.password = self.star.messenger_admin_password
        self.clients = {}  # Store clients for each agent
        self.message_handlers = {}  # Store custom handlers for each agent

    def import_handler(self, on_message_received):
        """Dynamically import the handler for the agent."""
        try:
            module = importlib.import_module(f"agents.{on_message_received}")
            handler = getattr(module, f"on_message_received_{on_message_received}")
            return handler
        except (ModuleNotFoundError, AttributeError) as e:
            logger.error(f"Error importing handler for {on_message_received}: {e}")
            return None

    async def add_agent(self, username, on_message_received):
        """Create a bot and assign a custom message handler to it."""
        agent_id = f"@{username}:{self.homeserver_URL.replace('https://', '').replace('http://', '')}"
        messenger_resident.register_user(agent_id, self.password, self.homeserver_URL)
        client = AsyncClient(self.homeserver_URL, agent_id)
        self.clients[agent_id] = client
        
        handler = self.import_handler(on_message_received)
        if handler:
            self.message_handlers[agent_id] = handler

    async def setup_agents(self, agent_dir_path):
        """Automatically scan the 'agents' directory and create bots for each agent."""
        agent_files = [
            f[:-3] for f in os.listdir(agent_dir_path) if f.endswith(".py") and f != "__init__.py"
        ]
        for agent in agent_files:
            await self.add_agent(agent, agent)

    async def set_group(self, group_alias, group_topic):
        """Set up a group with a given alias and topic."""
        check_url = f"{self.homeserver_URL}/_matrix/client/r0/directory/room/{group_alias}"
        headers = {
            "Authorization": f"Bearer {self.as_token}",
            "Content-Type": "application/json"
        }

        if "#" in group_alias:
            group_name = group_alias.split(":")[0][1:]
        else:
            group_name = group_alias

        check_response = requests.get(check_url, headers=headers)
        if check_response.status_code == 200:
            logger.info(f"Group with alias '{group_alias}' already exists.")
            return {"status": "exists", "message": f"Group with alias '{group_alias}' already exists."}
        elif check_response.status_code != 404:
            logger.error(f"Error checking group existence: {check_response.status_code} - {check_response.text}")
            return {"status": "error", "message": f"Error checking group: {check_response.status_code}"}

        url = f"{self.homeserver_URL}/_matrix/client/r0/createRoom"
        data = {
            "preset": "public_chat",
            "name": group_name,
            "topic": group_topic,
            "visibility": "public",
            "invite": [],
        }
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            logger.info(f"Group '{group_name}' created successfully.")
            return {"status": "created", "message": f"Group '{group_name}' created successfully."}
        else:
            logger.error(f"Error creating group: {response.status_code} - {response.text}")
            return {"status": "error", "message": f"Error creating group: {response.status_code}"}

    async def join_group(self, group_id=None, group_alias=None, agent_ids=None):
        """Allow agents to join a group."""
        if not agent_ids:
            agent_ids = list(self.clients.keys())

        if not group_id and not group_alias:
            logger.error("Error: No group ID or alias provided.")
            return

        if group_alias:
            resolve_url = f"{self.homeserver_URL}/_matrix/client/r0/directory/room/{group_alias}"
            headers = {
                "Authorization": f"Bearer {self.as_token}",
                "Content-Type": "application/json"
            }
            resolve_response = requests.get(resolve_url, headers=headers)
            if resolve_response.status_code == 200:
                group_id = resolve_response.json().get("room_id")
            else:
                logger.error(f"Error resolving room alias {group_alias}: {resolve_response.status_code} - {resolve_response.text}")
                return

        if not group_id:
            logger.error("Error: No valid room ID to join.")
            return

        for agent_id in agent_ids:
            client = self.clients.get(agent_id)
            if client:
                bot_token = client.access_token
                url = f"{self.homeserver_URL}/_matrix/client/r0/join/{group_id}"
                headers = {
                    "Authorization": f"Bearer {bot_token}",
                    "Content-Type": "application/json"
                }
                response = requests.post(url, headers=headers)
                if response.status_code == 200:
                    logger.info(f"Agent {agent_id} successfully joined group with room ID {group_id}.")
                else:
                    logger.error(f"Error joining group for agent {agent_id}: {response.status_code} - {response.text}")
            else:
                logger.error(f"Bot client for {agent_id} not found.")
