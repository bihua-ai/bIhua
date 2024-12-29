import asyncio
from nio import AsyncClient, MatrixRoom, RoomMessageText
import time

# Configuration constants
MATRIX_SERVER = "https://messenger.b1.shuwantech.com"  # Replace with your server
USERNAME = "@powerapp:messenger.b1.shuwantech.com"  # Replace with your Matrix username
PASSWORD = "thisismy.password"  # Replace with your password
DEFAULT_REPLY_TEXT = "请给出可执行指令。"  # Customize your reply

# Wrapper class for Messenger
class Messenger:
    def __init__(self, server: str, username: str, password: str):
        self.server = server
        self.username = username
        self.password = password
        self.client = AsyncClient(server, username)

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

    def message_callback(self, room: MatrixRoom, event: RoomMessageText):
        print(f"Received message in room {room.display_name} from {event.sender}: {event.body}")
        async def _message_callback():
            print(f"Received message in room {room.display_name} from {event.sender}: {event.body}")

            # if event.sender == self.username:  # Avoid responding to self
            #     return

            # _command = llm_translate.map_to_standard_string(user_input=event.body)
            # if _command.action is None or _command.action == "无行动":
            #     message_body = DEFAULT_REPLY_TEXT  # Fallback reply
            # else:
            #     message_body = _command.action

            # # Send reply to the same room
            # await self.client.room_send(
            #     room_id=room.room_id,
            #     message_type="m.room.message",
            #     content={
            #         "msgtype": "m.text",
            #         "body": message_body,
            #     },
            # )
            # print("Replied to the message!")

        return _message_callback

    async def start_listening(self):
        login_successful = await self.login()
        if not login_successful:
            return

        login_timestamp = int(time.time() * 1000)  # Convert to milliseconds

        # Register the callback
        self.client.add_event_callback(self.message_callback, RoomMessageText)

        # Start listening for messages (this is a blocking operation)
        print("Listening for messages...")
        await self.client.sync_forever(timeout=30000)  # Timeout in milliseconds

    async def stop_listening(self):
        await self.logout()


# Main function to run the messenger
async def main():
    messenger = Messenger(MATRIX_SERVER, USERNAME, PASSWORD)
    try:
        await messenger.start_listening()
    except KeyboardInterrupt:
        print("Messenger stopped.")
    finally:
        await messenger.stop_listening()


# Run the script
if __name__ == "__main__":
    asyncio.run(main())
