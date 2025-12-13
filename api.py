import uuid
import json
import asyncio
import base64
from logger import Colors, get_group_logger


class WebSocketClient:
    def __init__(self, websocket):
        self.websocket = websocket
        
    @property
    def echo(self):
        return str(uuid.uuid4())
    

    #点赞
    async def send_like(self,user_id ,times):
        data = {"action": "send_like", "params": {"user_id": user_id, "times": times}, "echo": self.echo}
        await self.websocket.send(json.dumps(data))

    #处理好友请求
    async def set_friend_add_request(self,flag,approve,remark):
        data = {"action": "set_friend_add_request", "params": {"flag": flag, "approve": approve, "remark": remark}, "echo": self.echo}
        await self.websocket.send(json.dumps(data))

    #处理入群请求
    async def set_group_add_request(self,flag,approve,reason):
        data = {"action": "set_group_add_request", "params": {"flag": flag, "approve": approve, "reason": reason}, "echo": self.echo}
        await self.websocket.send(json.dumps(data))

    #戳一戳
    async def poke(self, type, group_id ,user_id):
        if type == 1:
            data = {"action": "group_poke", "params": {"group_id": group_id, "user_id": user_id}, "echo": self.echo}
        else:
            data = {"action": "friend_poke", "params": {"user_id": user_id}, "echo": self.echo}
        await self.websocket.send(json.dumps(data))

    #发送消息
    async def send_message(self, type, send_id, message_id, message):
        if type == 1:
            data = {"action": "send_group_msg", "params": {"group_id": send_id, "message": [{"type": "reply", "data": {"id": message_id}}, {"type": "text", "data": {"text": f"{message}"}}]}, "echo": self.echo}
        else:
            data = {"action": "send_private_msg", "params": {"user_id": send_id, "message": [{"type": "reply", "data": {"id": message_id}}, {"type": "text", "data": {"text": f"{message}"}}]}, "echo": self.echo}
        await self.websocket.send(json.dumps(data))

    #发送at消息
    async def send_at_message(self,user_id, group_id, message):
        data = {"action": "send_group_msg", "params": {"group_id": group_id, "message": [{"type": "at", "data": {"qq": user_id}}, {"type": "text", "data": {"text": f"{message}"}}]}, "echo": self.echo}
        await self.websocket.send(json.dumps(data))

    #发送合并转发消息
    async def send_group_forward_msg(self, group_id, messages, default_uin=2582770985, default_name="乌萨奇大王"):
        """
        发送合并转发消息
        
        Args:
            group_id: 群组ID
            messages: 消息列表，每个消息可以是：
                      - 字符串：使用默认的 uin 和 name
                      - 字典：包含 text（必需）、uin（可选）、name（可选）
            default_uin: 默认的 uin，当消息为字符串或字典中未指定 uin 时使用
            default_name: 默认的 name，当消息为字符串或字典中未指定 name 时使用
        """
        # 如果传入的是单个字符串或字典，转换为列表
        if not isinstance(messages, list):
            messages = [messages]
        
        # 动态生成节点列表
        nodes = []
        for msg in messages:
            # 如果消息是字符串，转换为字典格式
            if isinstance(msg, str):
                msg_dict = {"text": msg}
            else:
                msg_dict = msg
            
            # 获取消息内容、uin 和 name
            text = msg_dict.get("text", "")
            uin = msg_dict.get("uin", default_uin)
            name = msg_dict.get("name", default_name)
            
            nodes.append({
                "type": "node",
                "data": {
                    "uin": uin,
                    "name": name,
                    "content": [{"type": "text", "data": {"text": text}}]
                }
            })
        
        data = {"action": "send_group_forward_msg", "params": {"group_id": group_id, "messages": nodes}, "echo": self.echo}
        await self.websocket.send(json.dumps(data))
        
    #发送图片消息
    async def send_image_message(self, type, send_id, message_id,message, image_path):
        # 读取图片文件并转换为base64
        try:
            loop = asyncio.get_event_loop()
            
            def read_and_encode():
                with open(image_path, 'rb') as image_file:
                    image_data = image_file.read()
                    return base64.b64encode(image_data).decode('utf-8')
            
            image_base64 = await loop.run_in_executor(None, read_and_encode)
        except Exception as e:
            print(f"{Colors.ERROR}读取图片文件失败: {e}{Colors.RESET}")
            if type == 1:  # 群消息
                logger = get_group_logger(send_id)
                logger.error(f"读取图片文件失败 - 图片路径: {image_path}, 错误: {e}")
            return
        
        if type == 1:
            data = {"action": "send_group_msg", "params": {"group_id": send_id, "message": [{"type": "reply", "data": {"id": message_id}}, {"type": "text", "data": {"text": message}}, {"type": "image", "data": {"file": f"base64://{image_base64}"}}]}, "echo": self.echo}
        else:
            data = {"action": "send_private_msg", "params": {"user_id": send_id, "message": [{"type": "reply", "data": {"id": message_id}}, {"type": "text", "data": {"text": message}}, {"type": "image", "data": {"file": f"base64://{image_base64}"}}]}, "echo": self.echo}
        await self.websocket.send(json.dumps(data))

