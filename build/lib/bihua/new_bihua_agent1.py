import asyncio, os, json
from dotenv import load_dotenv
import asyncio
from bihua_resident import Resident
from nio import AsyncClient, RoomMessageText, MatrixRoom,RoomMessageVideo, RoomMessageAudio, RoomMessageImage, RoomMessageFile
import datetime as dt
from typing import List
from pydantic import BaseModel
import time
import bihua_settings

# sudo docker build --no-cache -t bihua-python:latest -f Dockerfile_python .
# sudo docker run -p 8300:8000 --name bihua-python bihua-python:latest
# sudo docker ps -a
# sudo docker rm <dockder-id>
# digitalorganism / May221996


# llm_name will not be used but needs to be filled.
async def call_one_resident(homeserver, resident_id, password, email, llm_name):
    resident = Resident(homeserver, resident_id, password, email, llm_name)
    print(f"{resident_id} {password} {email} {llm_name}")

    try:
        #agent.star_client = AsyncClient(agent.homeserver, agent.user_name)  
        async def text_message_callback(room: MatrixRoom, event: RoomMessageText):
            await resident.on_text_message(room, event)

        async def image_message_callback(room: MatrixRoom, event: RoomMessageImage):
            await resident.on_image_message(room, event)

        async def audio_message_callback(room: MatrixRoom, event: RoomMessageAudio):
            await resident.on_audio_message(room, event)

        async def video_message_callback(room: MatrixRoom, event: RoomMessageText):
            await resident.on_video_message(room, event)

        async def file_message_callback(room: MatrixRoom, event: RoomMessageFile):
            await resident.on_file_message(room, event)

        resident.star_client.add_event_callback(text_message_callback, RoomMessageText)
        resident.star_client.add_event_callback(image_message_callback, RoomMessageImage)
        resident.star_client.add_event_callback(audio_message_callback, RoomMessageAudio)
        resident.star_client.add_event_callback(video_message_callback, RoomMessageVideo)
        resident.star_client.add_event_callback(file_message_callback, RoomMessageFile)

        await resident.star_client.login(password)

        await resident.dowmload_avatar_url()
        
        laslogin_timestamp_ms = dt.datetime.timestamp(dt.datetime.now()) * 1000 # event time is in ms, now() returns seconds
        resident.update_login_tiemstamp(laslogin_timestamp_ms)

        # await update_token_json(resident_id=resident.resident_id, access_token=resident.star_client.access_token, device_id=resident.star_client.device_id)

        await resident.star_client.sync_forever()
    except Exception as e:
        print(f"start_one_agent.start error. {resident_id}: {e}")

async def call_residents():
    # Get the list of residents to be called
    load_dotenv()
    STAR_RESIDENT_LIST_JSON_PATH = os.getenv("STAR_RESIDENT_LIST_JSON_PATH")
    STAR_SERVER_SYNAPSE_URL = os.getenv("STAR_SERVER_SYNAPSE_URL")
    print(STAR_SERVER_SYNAPSE_URL)


    with open(STAR_RESIDENT_LIST_JSON_PATH, 'r') as file:
        resident_list_json = json.load(file)

    try:

        coroutines = []
        count = 0
        for item in resident_list_json:
            bihua_settings.star_setup()
            bihua_settings.resident_or_group_home_setup(item["resident_id"])
            bihua_settings.resident_settings_save2(item["resident_id"], item["password"], item["email"], 
                                               last_login_timestamp_ms=0, last_sync_timestamp_ms=0, status=item["status"])
            time.sleep(1)
            count = count + 1
            print(f"loop count = {count}")
            # await call_one_resident(STAR_SERVER_SYNAPSE_URL, item["resident_id"], item["password"], item["email"], "openai")
            # print(item["resident_id"])
            if item["status"] == "enabled":
                # input "openai" is not used, legacy
                job = asyncio.create_task(call_one_resident(STAR_SERVER_SYNAPSE_URL, item["resident_id"], item["password"], item["email"], "openai"))
                coroutines.append(job)
            if count > 6:
                break
        futures = await asyncio.gather(*coroutines, return_exceptions=True)
        # for future in futures:
        #     if isinstance(future, Exception):
        #         print(f"An exception occurred: {future}")
    except Exception as e:
        print(f"call_residents {e}")

if __name__ == "__main__":
    asyncio.run(call_residents())

