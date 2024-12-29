from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os, json, uuid, nio
import instructor, openai
from openai import OpenAI



class Moonshot():
    api_key = "sk-hSBH7FZ89TBLfNFCeNfBa3url9v7EQY4NUVKIUPgvRIkm6WF",
    base_url = "https://api.moonshot.cn/v1"
    llm_model = "moonshot-v1-8k"
    temperature = 0.3
    instructor_model = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def chat(self, msg):
        llm_client = OpenAI(
            api_key = self.api_key,
            base_url = self.base_url,
        )
        completion = llm_client.chat.completions.create(
            model = self.model,
            temperature= self.temperature,
            messages = [
                {"role": "system", "content": "你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。"},
                {"role": "user", "content": msg}
            ]
        )
        result = completion.choices[0].message.content
        return result
    
    def get_moonshot_response_with_model(self, messages, data_model):
        try:
            client = instructor.from_openai(
                OpenAI(
                    api_key = "sk-hSBH7FZ89TBLfNFCeNfBa3url9v7EQY4NUVKIUPgvRIkm6WF",
                    base_url = "https://api.moonshot.cn/v1",
                ),
                mode=instructor.Mode.JSON,
            )

            # llamafamily/llama3-chinese-8b-instruct
            resp = client.chat.completions.create(
                model="moonshot-v1-auto",
                messages=messages,
                response_model=data_model,
            )
            return resp
        except AssertionError:
            print(f"{data_model}: AssertionError")
            return None
    
    # def get_moonshot_response_with_model(self, content, data_model):
    #     try:
    #         client = instructor.from_openai(
    #             OpenAI(
    #                 api_key = "sk-hSBH7FZ89TBLfNFCeNfBa3url9v7EQY4NUVKIUPgvRIkm6WF",
    #                 base_url = "https://api.moonshot.cn/v1",
    #             ),
    #             mode=instructor.Mode.JSON,
    #         )

    #         # llamafamily/llama3-chinese-8b-instruct
    #         resp = client.chat.completions.create(
    #             model="moonshot-v1-32k",
    #             messages=[
    #                 {
    #                     "role": "user",
    #                     "content": f"{content}",
    #                 }
    #             ],
    #             response_model=data_model,
    #         )
    #         return resp
    #     except AssertionError:
    #         # client.close()
    #         print(f"{data_model}: AssertionError")
    #         return None

