from pydantic import BaseModel, Field
from nio import AsyncClient
import httpx
from typing import Optional, List
from bihua_one_star import Star
from messenger_resident import Resident
from models_moonshot import Moonshot
import llm_models
from  openai import OpenAI
from status_definitions import RegisterStatus, CheckCrudStatus, LoginStatus, CrudStatus
import bihua_api
from bihua_api import AdminLoginRequest

class RequestMatcher(BaseModel):
    request_name: str = Field(..., description="The name of the request")
    api_name: str = Field(..., description="The associated API name")
    reason: str = Field(..., description="The associated API name")


async def chat_with_api(
    resident_id: str,
    room_id: str,
    message: str,
    msg_receivers: Optional[List[str]] = None,
    text_files: Optional[List[str]] = None,
    images: Optional[List[str]] = None,
    audios: Optional[List[str]] = None,
    videos: Optional[List[str]] = None
):
    moonshot_service = Moonshot()
    # 1. take message and api model, ask llm_model, to get model class. If missing, ask questions till collect all info.
    # moonshot_model_info = llm_models.get_model_info()



    data_file = "/opt/bihua/star_dev/bihua/messenger/api.json"
    with open(data_file, 'r') as f:
        data = f.read()

    escaped_json_str = data.replace("{", "{{").replace("}", "}}")
    statement = f"""
    context: {escaped_json_str}

    user message: {message}

    question: in the context, pick the matching request that match user message the best.
    """
    request:RequestMatcher = moonshot_service.get_moonshot_response_with_model(statement, RequestMatcher)

    # 2. check message
    if request.request_name == "AdminLoginRequest":
        api_model: bihua_api.AdminLoginRequest = moonshot_service.get_moonshot_response_with_model(statement, bihua_api.AdminLoginRequest)
        print(api_model)

        login_status: LoginStatus = bihua_api.admin_login(resident_id = api_model.resident_id, password = api_model.resident_id)
        return login_status



    elif request.request_name == "ChangeUserDisplayNameRequest":
        api_model = moonshot_service.get_moonshot_response_with_model(statement, bihua_api.ChangeUserDisplayNameRequest)
    elif request.request_name == "ChangeUserRoleRequest":
        api_model = moonshot_service.get_moonshot_response_with_model(statement, bihua_api.ChangeUserRoleRequest)
    elif request.request_name == "ChangeUserStateRequest":
        api_model = moonshot_service.get_moonshot_response_with_model(statement, bihua_api.ChangeUserStateRequest)
    elif request.request_name == "ChangeUserTypeRequest":
        api_model = moonshot_service.get_moonshot_response_with_model(statement, bihua_api.ChangeUserTypeRequest)
    elif request.request_name == "GetAllUsersRequest":
        api_model = moonshot_service.get_moonshot_response_with_model(statement, bihua_api.GetAllUsersRequest)
    else: # unknown
        print("cannot understand your request.")



   







    url = "http://your-fastapi-server.com/api/chat"  # Replace with your FastAPI server URL

    payload = {
        "username": username,
        "password": password,
        "access_token": access_token,
        "room_id": room_id,
        "msg_receivers": msg_receivers,
        "message": message,
        "text_files": text_files,
        "images": images,
        "audios": audios,
        "videos": videos
    }

    # Filter out any None values from the payload
    payload = {key: value for key, value in payload.items() if value is not None}

    # Make an asynchronous request to the FastAPI endpoint
    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=payload)

    # Return the API's response
    return response.json()  # Or response.text(), depending on the response format
