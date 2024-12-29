import asyncio
import os
import json
import sys
from dotenv import load_dotenv
from messenger_resident import Resident
import messenger_resident
from bihua_one_star import Star
from bihua_logging import get_logger
from status_definitions import AgentStatus
import bihua_api
from nio import LoginError, AsyncClient, RoomMemberEvent, RoomMessageText, MatrixRoom, RoomMessageVideo, RoomMessageAudio, RoomMessageImage, RoomMessageFile
import datetime as dt
from typing import List
from pydantic import BaseModel
import time
import subprocess
import signal

logger = get_logger()

resident = None

def handle_exit(signum, frame):
    logger.info(f"Received signal {signum}, exiting gracefully...{resident.resident_id}")
    sys.exit(0)  # Exit the resident

signal.signal(signal.SIGINT, handle_exit)

async def on_text_message(room, event):
    pass

async def start_resident_messaging(resident_id=None, password=None, access_token=None):
    global resident
    if resident_id is None:
        # Use admin to run if resident_id is not provided
        try:
            _star = Star()
            resident_id = _star.messenger_admin_id
        except Exception as e:
            logger.error(f"{AgentStatus.EXCEPTION} Error fetching Star instance: {e}")
            return

    try:
        logger.info(f"Starting messaging for resident_id: {resident_id}")
        resident = Resident(resident_id)

        # Message callbacks
        async def text_message_callback(room: MatrixRoom, event: RoomMessageText):
            logger.debug(f"Received text message in room {room.room_id}")
            await on_text_message(room, event)

        async def image_message_callback(room: MatrixRoom, event: RoomMessageImage):
            logger.debug(f"Received image message in room {room.room_id}")
            await resident.on_image_message(room, event)

        async def audio_message_callback(room: MatrixRoom, event: RoomMessageAudio):
            logger.debug(f"Received audio message in room {room.room_id}")
            await resident.on_audio_message(room, event)

        async def video_message_callback(room: MatrixRoom, event: RoomMessageVideo):
            logger.debug(f"Received video message in room {room.room_id}")
            await resident.on_video_message(room, event)

        async def file_message_callback(room: MatrixRoom, event: RoomMessageFile):
            logger.debug(f"Received file message in room {room.room_id}")
            await resident.on_file_message(room, event)
        async def room_member_callback(event: RoomMemberEvent):
            logger.debug(f"Received roommember event in room {event.membership}")
            await resident.on_room_member_event(event)

        # Add event callbacks
        resident.messenger_client.add_event_callback(text_message_callback, RoomMessageText)
        resident.messenger_client.add_event_callback(image_message_callback, RoomMessageImage)
        resident.messenger_client.add_event_callback(audio_message_callback, RoomMessageAudio)
        resident.messenger_client.add_event_callback(video_message_callback, RoomMessageVideo)
        resident.messenger_client.add_event_callback(file_message_callback, RoomMessageFile)
        resident.messenger_client.add_event_callback(room_member_callback, RoomMemberEvent)

        valid_access_token = False
        if access_token and len(access_token) > 2:
            logger.info(f"{resident_id}'s access_token provided, validating...")
            resident.messenger_client.access_token = access_token
            resident.messenger_client.user_id = resident_id
            try:
                test_url = await resident.messenger_client.get_avatar()  # Test token validity
                valid_access_token = True
                logger.info(f"Login with access token successful. Avatar URL: {test_url}")
            except Exception as e:
                valid_access_token = False
                logger.error(f"{AgentStatus.ERROR} Access token validation failed: {e}")
                access_token = ""

        if not valid_access_token:
            # Attempt login with password if token validation fails
            logger.info(f"Attempting login with password for {resident_id}")
            response = await resident.messenger_client.login(password)
            if isinstance(response, LoginError):
                logger.error(f"{AgentStatus.ERROR} Login failed: Invalid user or password for {resident_id}")
                return
            else:
                access_token = resident.messenger_client.access_token
                resident.access_token = access_token
                logger.info(f"Login successful, access token: {access_token}")

        # Record the last login timestamp
        last_login_timestamp_ms = dt.datetime.timestamp(dt.datetime.now()) * 1000  # ms precision
        resident.last_login_timestamp_ms(last_login_timestamp_ms)
        messenger_resident.resident_settings_update(resident_id=resident_id, last_login_timestamp_ms=last_login_timestamp_ms)

        # Start syncing with the messaging service
        logger.info(f"Syncing messaging client for {resident_id}...")
        await resident.messenger_client.sync_forever(3000)
        logger.debug(f"Sync response: {sync_response}")

    except Exception as e:
        logger.error(f"{AgentStatus.EXCEPTION} Unexpected error in start_resident_messaging for {resident_id}: {e}")
        raise

# Example of running the messaging system with asyncio
if __name__ == "__main__":
    try:
        asyncio.run(start_resident_messaging(resident_id=None, password=None, access_token=None))
    except Exception as e:
        logger.error(f"{AgentStatus.EXCEPTION} Failed to start resident messaging: {e}")
        sys.exit(1)
