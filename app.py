import asyncio
import json
import websockets
import os
import sys
from logger import Colors, get_global_error_logger, get_group_logger
from api import WebSocketClient
import handlers

VERSION = "1.0.0"

# 读取配置文件
def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        error_msg = f"配置文件不存在: {config_path}"
        print(f"{Colors.ERROR}{error_msg}{Colors.RESET}")
        sys.exit(1)

config = load_config()

async def receive_messages(ws, api, config):
    bot_user_id = config.get("bot_user_id", "")
    while True:
        data = json.loads(await ws.recv())
        post_type = data.get("post_type")
        notice_type = data.get("notice_type")
        sub_type = data.get("sub_type")
        request_type = data.get("request_type")

        if data.get("message_type") == "group":
            message_id = data.get("message_id")
            message_list = data.get("message", [])
            message = None
            for msg in message_list:
                if msg.get("type") == "text":
                    message = msg.get("data", {}).get("text", "")
                    break
            user_id = data.get("user_id")
            group_id = data["group_id"]
            group_name = data.get("group_name", "")
            sender_nickname = data.get("sender", {}).get("nickname", "")
            at_qq = next((msg.get("data", {}).get("qq") for msg in message_list if msg.get("type") == "at"), None)
            print(f"{Colors.INFO}(群号: {group_id} | 群名: {group_name}) (发送者ID: {user_id} | 发送者: {sender_nickname}) 内容: {message}{Colors.RESET}")
            # 记录消息日志
            logger = get_group_logger(group_id)
            logger.info(f"群名: {group_name} | 发送者ID: {user_id} | 发送者: {sender_nickname} | 内容: {message}")


            if at_qq is not None and str(at_qq) == str(bot_user_id):
                at_message = data.get("message", [])
                asyncio.create_task(handlers.ai_chat_handler(at_message, group_id, message_id, user_id))
            elif message:
                msg = message.strip().lower().lstrip('.')
                if msg.startswith("wiki") or msg.startswith("查询") or msg.startswith("搜索"):
                    tag_key = (group_id, user_id)
                    if tag_key in handlers.wiki_waiting_tags:
                        await api.send_message(1, group_id, message_id, "乌~啦～上一个查询未完成！")
                    else:
                        asyncio.create_task(handlers.handle_wiki(message, group_id, message_id, user_id))
                elif message.strip().isdigit():
                    asyncio.create_task(handlers.choose_wiki(message, group_id, message_id, user_id))
                elif message == "赞我":
                    await api.send_message(1, group_id, message_id, "乌~啦～！收已经给你点赞啦！")
                    await api.send_like(user_id, 20)
                else:
                    # 检查消息中是否包含 https://smapi.io/log 链接
                    asyncio.create_task(handlers.handle_smapi(message_list, group_id, message_id, user_id))
                    asyncio.create_task(handlers.poke_handler(1, group_id, bot_user_id, user_id, None))
            else:
                asyncio.create_task(handlers.poke_handler(1, group_id, bot_user_id, user_id, None))
        elif sub_type == "poke":
            user_id = data.get("user_id")
            target_id = str(data.get("target_id"))
            group_id = str(data.get("group_id"))
            asyncio.create_task(handlers.poke_handler(0, group_id, bot_user_id, user_id, target_id))
        # 处理入群事件
        elif post_type == "notice" and notice_type == "group_increase":
            group_id = data.get("group_id")
            user_id = data.get("user_id")
            if str(user_id) == str(bot_user_id):
                return
            else:
                asyncio.create_task(handlers.group_increase_handler(group_id, user_id))
        # 处理好友请求
        elif post_type == "request" and request_type == "friend":
            flag = data.get("flag")
            user_id = data.get("user_id")
            await api.set_friend_add_request(flag, True, None)
            await asyncio.sleep(2)
            await api.send_message(2, user_id, None, "乌~啦～！你好！")
        # 处理被邀请入群请求
        elif post_type == "request" and request_type == "group" and sub_type == "invite":
            flag = data.get("flag")
            user_id = data.get("user_id")
            await api.set_group_add_request(flag, True, None)
            await asyncio.sleep(2)
            await api.send_message(2, user_id, None, "乌~啦～！ 已经同意啦！")

async def main():
    print(f"{Colors.INFO}v{VERSION}{Colors.RESET}")
    if config.get("access_token") and config.get("access_token", "").strip():
        uri = f"ws://{config['ip']}?access_token={config['access_token']}"
    else:
        uri = f"ws://{config['ip']}"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print(f"{Colors.INFO}WebSocket连接成功{Colors.RESET}")
                api = WebSocketClient(websocket)
                # 初始化 handlers
                handlers.init_handlers(api, config)
                receive_task = asyncio.create_task(receive_messages(websocket, api, config))
                await receive_task
        except websockets.exceptions.ConnectionClosed:
            print(f"{Colors.INFO}WebSocket连接已关闭，5秒后重连...{Colors.RESET}")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"{Colors.ERROR}WebSocket连接错误: {e}{Colors.RESET}")
            logger = get_global_error_logger()
            logger.error(f"WebSocket连接错误 - 错误: {e}")
            print(f"{Colors.INFO}5秒后尝试重连...{Colors.RESET}")
            await asyncio.sleep(5)

asyncio.run(main())

