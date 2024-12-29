from models_moonshot import Moonshot
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os, json, uuid, nio
import instructor, openai
from openai import OpenAI
import bihua_api

class RequestMatcher(BaseModel):
    request_name: str = Field(..., description="The name of the request")
    api_name: str = Field(..., description="The associated API name")
    reason: str = Field(..., description="The associated API name")


moonshot_service = Moonshot()
messages = [
                {
                    "role": "system",
                    "content": "你是 Kimi，由 Moonshot AI 提供的软件工程师人工智能助手，你熟悉软件需求、代码分析、测试场景设计和生成、更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。",
                },
                {
                    "role": "user",
                    "content": f"请根据信息，帮助选择匹配函数",
                }
            ]

data_file = "/opt/bihua/star_dev/bihua/messenger/api2.json"
with open(data_file, 'r') as f:
    data = f.read()

request = "我要登录系统，使用用户名admin，密码abc123"

escaped_json_str = data.replace("{", "{{").replace("}", "}}")
content = f"""
context: {escaped_json_str}

user message: {request}

question: in the context, pick the matching request that match user message the best.
"""

message = {
    "role": "user",
    "content": content
}   

messages.append(message)

reaponse = moonshot_service.get_moonshot_response_with_model(messages, RequestMatcher)

print(reaponse)

messages.pop(len(messages)-1)

message = {
        "role": "user",
    "content": request
}

messages.append(message)

reaponse = moonshot_service.get_moonshot_response_with_model(messages, bihua_api.AdminLoginRequest)
print(reaponse)