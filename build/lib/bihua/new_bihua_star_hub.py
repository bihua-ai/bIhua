from pydantic import BaseModel
from nio import LoginError, AsyncClient, RoomMemberEvent, RoomMessageText, MatrixRoom, RoomMessageVideo, RoomMessageAudio, RoomMessageImage, RoomMessageFile
import time
from bihua_one_star import Star
from messenger_group import Group
from messenger_resident import Resident
import messenger_resident, messenger_group

def setup_resident(resident_id):
    print("Setting up resident...")

    resident = Resident(resident_id)
    messenger_resident.create_update_resident_settings(resident_id)


# save message

def setup_group(group_id):
    print("Setting up group...")
    messenger_group.create_update_group_settings(group_id)

def setup(resident_id, group_id):
    print("Setting up resident group...")
    setup_resident(resident_id)
    setup_group(group_id)

class Hub:
    def __init__(self, server_url, username, password):
        self.server_url = server_url

        # get userid
        if server_url.startswith("https://"):
            self.servername = server_url[8:]  # Remove 'https://'
        elif server_url.startswith("http://"):
            self.servername = server_url[7:]  # Remove 'http://'
        else:
            self.servername = server_url  # No protocol, just assign directly
        self.user_id = f"@{username}:{self.servername}"

        # get password
        self.password = password

        self.star = Star()

        # create client
        self.client = AsyncClient(self.server_url, self.star.messenger_admin_id)

    async def login(self):
        response = await self.client.login(self.star.messenger_admin_password)
        if response:
            print("Logged in successfully!")
        else:
            print(f"Failed to log in: {response}")
            return False
        return True

    async def logout(self):
        await self.client.logout()
        await self.client.close()

    
    def bind_message_handler(self, message_handler, event_type):
        self.client.add_event_callback(message_handler, event_type)

    async def start_listening(self):
        login_successful = await self.login() # login as admin
        if not login_successful:
            print("Log in failed...")
            return

        login_timestamp = int(time.time() * 1000)  # Convert to milliseconds

        # Register the callback
        # self.client.add_event_callback(message_callback, RoomMessageText)
        # self.bind_message_handler(message_handler, RoomMessageText)

        # Start listening for messages (this is a blocking operation)
        print("Listening for messages...")
        await self.client.sync_forever(timeout=30000)  # Timeout in milliseconds

    async def stop_listening(self):
        print("Log out...")
        await self.logout()

    