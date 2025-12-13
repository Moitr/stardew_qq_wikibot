import json
import os
from openai import AsyncOpenAI

# 读取配置文件
def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

config = load_config()

# 公共 OpenAI 配置
openai_config = config.get("openai", {})
API_KEY = openai_config.get("api_key", "")
BASE_URL = openai_config.get("base_url", "")

# 普通聊天配置
ai_config = config.get("ai_chat", {})
SYSTEM_PROMPT = ai_config.get("system_prompt", "")
MODEL = ai_config.get("model", "")

client = AsyncOpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

# SMAPI AI配置
ai_config_smapi = config.get("ai_chat_smapi", {})
SYSTEM_PROMPT_SMAPI = ai_config_smapi.get("system_prompt", "")
MODEL_SMAPI = ai_config_smapi.get("model", "")

client_smapi = AsyncOpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

async def get_ai_response(prompt: str) -> str:
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt}
        ],
        stream=True
    )

    full_response = ""
    async for chunk in response:
        if not chunk.choices:
            continue
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_response += content
        if chunk.choices[0].delta.reasoning_content:
            pass
    
    return full_response

async def get_ai_response_smapi(prompt: str) -> str:
    response = await client_smapi.chat.completions.create(
        model=MODEL_SMAPI,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT_SMAPI},
            {'role': 'user', 'content': prompt}
        ],
        stream=True
    )

    full_response = ""
    async for chunk in response:
        if not chunk.choices:
            continue
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_response += content
        if chunk.choices[0].delta.reasoning_content:
            pass
    
    return full_response

