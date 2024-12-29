from pydantic import BaseModel
from nio import LoginError, AsyncClient, RoomMemberEvent, RoomMessageText, MatrixRoom, RoomMessageVideo, RoomMessageAudio, RoomMessageImage, RoomMessageFile
import time
from bihua_one_star import Star

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

        # create client
        self.client = AsyncClient(self.server_url, self.user_id)

    async def login(self):
        response = await self.client.login(self.password)
        if response:
            print("Logged in successfully!")
        else:
            print(f"Failed to log in: {response}")
            return False
        return True

    async def logout(self):
        await self.client.logout()
        await self.client.close()

    # this will be called dyring initialization
    def preprocess(self):
        # create agent and grpup data directory if not created
        # save chat data

        pass
    
    def bind_message_handler(self, message_handler, event_type):
        self.client.add_event_callback(message_handler, event_type)

    async def start_listening(self):
        login_successful = await self.login()
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

    