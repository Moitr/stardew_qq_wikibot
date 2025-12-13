import asyncio
import json
import time
import random
import re
import os
from datetime import datetime, date
import wiki
from logger import Colors, get_group_logger
import openai_client
from smapi import check_log_parse_error

# 全局变量，通过 init_handlers 初始化
api = None
config = None
wiki_waiting_tags = {}  # {(group_id, user_id): result}
wiki_rate_limit = {}  # {(group_id, user_id): {'count': int, 'reset_time': float}}
smapi_rate_limit = {}  # {(group_id, user_id): {'last_use_time': float}}  # 用户+群组的10分钟限制
smapi_daily_limit = {'count': 0, 'date': None}  # 全局每日限制：{'count': int, 'date': date}

def init_handlers(api_client, config_dict):
    """初始化处理器，设置 api 客户端和配置"""
    global api, config
    api = api_client
    config = config_dict

# 戳一戳处理
async def poke_handler(type, group_id, bot_user_id, user_id, target_id):
    # 检查是否启用戳一戳功能
    poke_config = config.get("poke", {})
    if not poke_config.get("enabled", True):
        return
    
    if type == 1:
        if random.random() < 0.02:
            await api.poke(1, group_id, user_id)
            print(f"{Colors.INFO}戳一戳 - 群号: {group_id} | 目标用户ID: {user_id}{Colors.RESET}")
            logger = get_group_logger(group_id)
            logger.info(f"戳一戳 - 群号: {group_id} | 目标用户ID: {user_id}")
    else:
        if target_id == bot_user_id:
            poke_messages = poke_config.get("messages", [""])
            random_message = random.choice(poke_messages)
            await api.send_message(1, group_id, None, random_message)
            await api.poke(1, group_id, user_id)

# 入群事件处理
async def group_increase_handler(group_id, user_id):
    # 检查是否启用入群欢迎功能
    group_increase_config = config.get("group_increase", {})
    if not group_increase_config.get("enabled", True):
        return
    
    welcome_message = group_increase_config.get("welcome_message", " 你好！欢迎加入！")
    await api.send_at_message(user_id, group_id, welcome_message)
    print(f"{Colors.INFO}成员入群 - 群号: {group_id} | 新成员ID: {user_id}{Colors.RESET}")
    logger = get_group_logger(group_id)
    logger.info(f"成员入群 - 群号: {group_id} | 新成员ID: {user_id}")

# Wiki 指令处理
async def handle_wiki(message, group_id, message_id, user_id):
    try:
        # 检查是否匹配 wiki 指令（支持 .wiki、wiki、查询，带或不带空格）
        message_stripped = message.strip() if message else ""
        message_lower = message_stripped.lower()
        
        # 去除开头的点（如果存在）
        if message_lower.startswith("."):
            message_lower = message_lower[1:]
            message_stripped = message_stripped[1:]
        
        # 检查是否以 wiki、查询 或 搜索 开头
        keyword = None
        keyword_len = 0
        if message_lower.startswith("wiki"):
            keyword = "wiki"
            keyword_len = 4
        elif message_lower.startswith("查询"):
            keyword = "查询"
            keyword_len = 2
        elif message_lower.startswith("搜索"):
            keyword = "搜索"
            keyword_len = 2
        
        if keyword:
            # 检查频率限制
            tag_key = (group_id, user_id)
            current_time = time.time()
            
            # 从配置文件读取限制参数
            rate_limit_config = config.get('wiki_rate_limit', {})
            max_queries = rate_limit_config.get('max_queries')
            time_window = rate_limit_config.get('time_window')
            
            # 如果记录存在且未过期，检查计数
            if tag_key in wiki_rate_limit:
                rate_info = wiki_rate_limit[tag_key]
                if current_time < rate_info['reset_time']:
                    # 仍在限制时间窗口内
                    if rate_info['count'] >= max_queries:
                        # 超过限制
                        remaining_time = int(rate_info['reset_time'] - current_time)
                        try:
                            await api.send_message(1, group_id, message_id, f"查询频繁，请 {remaining_time} 秒后再试~")
                        except Exception as e:
                            print(f"{Colors.ERROR}发送消息失败: {e}{Colors.RESET}")
                        return
                    else:
                        # 增加计数
                        rate_info['count'] += 1
                else:
                    # 时间窗口已过期，重置
                    wiki_rate_limit[tag_key] = {'count': 1, 'reset_time': current_time + time_window}
            else:
                # 首次查询，创建记录
                wiki_rate_limit[tag_key] = {'count': 1, 'reset_time': current_time + time_window}
            
            # 提取搜索内容：从关键词之后开始提取
            if len(message_stripped) > keyword_len:
                # 检查关键词之后是否有空格
                if len(message_stripped) > keyword_len and message_stripped[keyword_len] == ' ':
                    search_content = message_stripped[keyword_len + 1:].strip()
                else:
                    search_content = message_stripped[keyword_len:].strip()
            else:
                search_content = ""
            if search_content:
                try:
                    result = await wiki.Search(search_content)
                except Exception as e:
                    print(f"{Colors.ERROR}Wiki搜索失败: {e}{Colors.RESET}")
                    logger = get_group_logger(group_id)
                    logger.error(f"Wiki搜索失败 - 搜索内容: {search_content}, 错误: {e}")
                    try:
                        await api.send_message(1, group_id, message_id, "查询失败，请重试")
                    except:
                        pass
                    return

                wiki_waiting_tags[tag_key] = result

                if result['type'] == 0:
                    try:
                        await api.send_message(1, group_id, message_id, result['text'])
                    except Exception as e:
                        print(f"{Colors.ERROR}发送消息失败: {e}{Colors.RESET}")
                        logger = get_group_logger(group_id)
                        logger.error(f"发送消息失败 - 错误: {e}")
                    
                    try:
                        image = await wiki.SearchResult(result['results'][0]['full_url'])
                        await api.send_image_message(1, group_id, message_id, search_content, image)
                        del wiki_waiting_tags[tag_key]
                        return
                    except Exception as e:
                        print(f"{Colors.ERROR}截图失败: {e}{Colors.RESET}")
                        logger = get_group_logger(group_id)
                        logger.error(f"截图失败 - 错误: {e}")
                        if tag_key in wiki_waiting_tags:
                            del wiki_waiting_tags[tag_key]
                        return
                elif result['type'] == -1:
                    # 没有搜索结果，直接发送消息，不等待选择
                    try:
                        await api.send_message(1, group_id, message_id, result['text'])
                    except Exception as e:
                        print(f"{Colors.ERROR}发送消息失败: {e}{Colors.RESET}")
                        logger = get_group_logger(group_id)
                        logger.error(f"发送消息失败 - 错误: {e}")
                    if tag_key in wiki_waiting_tags:
                        del wiki_waiting_tags[tag_key]
                    return
                else:
                    # type == 1，有多个结果，显示选择提示
                    try:
                        await api.send_message(1, group_id, message_id, result['text'] + '\n请在60秒发送：1-' + str(result['wiki_len']))
                    except Exception as e:
                        print(f"{Colors.ERROR}发送消息失败: {e}{Colors.RESET}")
                        logger = get_group_logger(group_id)
                        logger.error(f"发送消息失败 - 错误: {e}")
                

                # 创建60秒倒计时任务
                async def countdown_message():
                    try:
                        await asyncio.sleep(60)
                        if tag_key in wiki_waiting_tags:
                            try:
                                await api.send_message(1, group_id, message_id, "回复超时！")
                            except:
                                pass
                            del wiki_waiting_tags[tag_key]
                    except Exception as e:
                        print(f"{Colors.ERROR}倒计时任务错误: {e}{Colors.RESET}")
                        logger = get_group_logger(group_id)
                        logger.error(f"倒计时任务错误 - 错误: {e}")
                
                asyncio.create_task(countdown_message())
            else:
                try:
                    await api.send_message(1, group_id, message_id, "乌~啦～输入要查询的内容，如.Wiki 乌·呀·咿·哈")
                except Exception as e:
                    print(f"发送消息失败: {e}")
    except Exception as e:
        print(f"{Colors.ERROR}handle_wiki 发生未预期的错误: {e}{Colors.RESET}")
        if 'group_id' in locals():
            logger = get_group_logger(group_id)
            import traceback
            logger.error(f"handle_wiki 发生未预期的错误 - 错误: {e}\n{traceback.format_exc()}")
        import traceback
        traceback.print_exc()

# Wiki选择指令处理
async def choose_wiki(message, group_id, message_id, user_id):
    try:
        # 检查消息是否为纯数字
        if not message or not message.strip().isdigit():
            return
        
        tag_key = (group_id, user_id)
        
        # 如果没有待查询的，静默返回，不回复
        if tag_key not in wiki_waiting_tags:
            # 处理戳一戳
            asyncio.create_task(poke_handler(1, group_id, None, user_id, None))
            return
        
        try:
            choice_num = int(message.strip())
            result = wiki_waiting_tags.get(tag_key)
            
            # 如果结果被删除了，静默返回
            if result is None:
                # 处理戳一戳
                asyncio.create_task(poke_handler(1, group_id, None, user_id, None))
                return
            
            if not result.get('results') or len(result['results']) == 0:
                # 删除无效结果，防止倒计时任务发送超时
                if tag_key in wiki_waiting_tags:
                    del wiki_waiting_tags[tag_key]
                return
            
            if choice_num < 1 or choice_num > len(result['results']):
                # 数字超出范围，回复提示
                try:
                    await api.send_message(1, group_id, message_id, f"请输入有效的数字（1-{len(result['results'])}）")
                except Exception as e:
                    print(f"{Colors.ERROR}发送消息失败: {e}{Colors.RESET}")
                # 不删除，让用户重新选择
                return
            
            selected_result = result['results'][choice_num - 1]
            selected_url = selected_result['full_url']
            selected_title = selected_result['title']
            
            try:
                infobox_text = await wiki.get_infobox_text(selected_url)
                await api.send_message(1, group_id, message_id, f"{infobox_text}\n查看更多：{selected_url}")
                image = await wiki.SearchResult(selected_url)
                await api.send_image_message(1, group_id, message_id, selected_title, image)
                result = wiki_waiting_tags.pop(tag_key, None)
            except Exception as e:
                print(f"{Colors.ERROR}截图失败: {e}{Colors.RESET}")
                logger = get_group_logger(group_id)
                logger.error(f"截图失败 - 选择序号: {choice_num}, 错误: {e}")
                
        except (ValueError, IndexError, KeyError) as e:
            print(f"{Colors.ERROR}选择结果时出错: {e}{Colors.RESET}")
            logger = get_group_logger(group_id)
            logger.error(f"选择结果时出错 - 选择序号: {message}, 错误: {e}")
            if tag_key in wiki_waiting_tags:
                del wiki_waiting_tags[tag_key]
    except Exception as e:
        print(f"{Colors.ERROR}choose_wiki 发生未预期的错误: {e}{Colors.RESET}")
        if 'group_id' in locals():
            logger = get_group_logger(group_id)
            import traceback
            logger.error(f"choose_wiki 发生未预期的错误 - 错误: {e}\n{traceback.format_exc()}")
        import traceback
        traceback.print_exc()

# 链接SMapi
async def handle_smapi(message_list, group_id, message_id, user_id):
    # 提取所有文本消息片段
    text_parts = [msg.get("data", {}).get("text", "") for msg in message_list if msg.get("type") == "text"]
    full_message = " ".join(text_parts)
        
    # 匹配 https://smapi.io/log/ 链接（不包含括号）
    url_pattern = r'https://smapi\.io/log/[^\s()]*'
    match = re.search(url_pattern, full_message)
        
    if match:
        tag_key = (group_id, user_id)
        current_time = time.time()
        
        # 从配置文件读取限制参数
        rate_limit_config = config.get('smapi_rate_limit', {})
        time_window = rate_limit_config.get('time_window', 600)  # 默认10分钟 = 600秒
        max_daily_uses = rate_limit_config.get('max_daily_uses', 20)
        max_chars = rate_limit_config.get('max_log_chars', 50000)
        
        # 检查用户+群组的10分钟限制（原来的限制）
        if tag_key in smapi_rate_limit:
            rate_info = smapi_rate_limit[tag_key]
            if current_time < rate_info['last_use_time'] + time_window:
                # 仍在限制时间窗口内
                remaining_time = int(rate_info['last_use_time'] + time_window - current_time)
                await api.send_message(1, group_id, message_id, f"查询频繁，请 {remaining_time} 秒后再试！")
                return
        
        # 全局每日限制检查
        today = date.today()
        
        # 如果是新的一天，重置计数
        if smapi_daily_limit['date'] != today:
            smapi_daily_limit['count'] = 0
            smapi_daily_limit['date'] = today
        
        # 检查是否超过每日限制
        if smapi_daily_limit['count'] >= max_daily_uses:
            await api.send_message(1, group_id, message_id, f"今天已经使用了 {max_daily_uses} 次，请明天再试哦！")
            return
        
        extracted_url = match.group(0)
        result = await check_log_parse_error(extracted_url)
        if result:
            smapi_rate_limit[tag_key] = {'last_use_time': current_time} 
            smapi_daily_limit['count'] += 1  # 增加全局每日计数
            await api.send_message(1, group_id, message_id, "正在分析日志，请耐心等待！")
            # 读取文件内容
            with open(result, 'r', encoding='utf-8') as f:
                log_content = f.read()

            # 限制日志长度
            if len(log_content) > max_chars:
                log_content = f"[日志过长，仅显示最后 {max_chars} 字符]\n" + log_content[-max_chars:]
            
            # 将日志内容传给AI分析
            ai_response_smapi = await openai_client.get_ai_response_smapi(log_content)
            ai_response_smapi = ai_response_smapi.replace('**', '')
            await api.send_at_message(user_id, group_id, " 日志分析完成!")
            forward_messages = [
                {"text": "由于deepseekR1模型的token太贵了，所以不得不添加限制...", "uin": 3014518835, "name": "Moite"},
                {"text": "如果还是无法解决可以加群：星露谷物语手机版模组交流群（611726395）来询问哦！", "uin": 1497551537, "name": "yukino"},
                {"text": ai_response_smapi, "uin": 2582770985, "name": "乌萨奇大王"}
            ]
            await api.send_group_forward_msg(group_id, forward_messages)
        else:
            await api.send_message(1, group_id, message_id, "解析失败，请确保链接正确哦！")
        

# AI回复处理
async def ai_chat_handler(at_message, group_id, message_id, user_id):

    text_content = "".join(msg.get("data", {}).get("text", "") for msg in at_message if msg.get("type") == "text")
    text_content = text_content.lstrip()

    if text_content == "":
        await api.send_message(1, group_id, message_id, "你好，有什么想和我说的嘛？")
        return

    if "赞我" in text_content:
        await api.send_message(1, group_id, message_id, "已经给你点赞啦！")
        await api.send_like(user_id, 20)
        return

    # 检查是否为 wiki/查询/搜索 指令
    msg = text_content.strip().lower().lstrip('.')
    if msg.startswith("wiki") or msg.startswith("查询") or msg.startswith("搜索"):
        tag_key = (group_id, user_id)
        if tag_key in wiki_waiting_tags:
            await api.send_message(1, group_id, message_id, "上一个查询未完成！")
        else:
            asyncio.create_task(handle_wiki(text_content, group_id, message_id, user_id))
        return

    try:
        ai_response = await openai_client.get_ai_response(text_content)
        await api.send_message(1, group_id, message_id, ai_response)
    except Exception as e:
        print(f"{Colors.ERROR}AI回复失败: {e}{Colors.RESET}")
        logger = get_group_logger(group_id)
        logger.error(f"AI回复失败 - 消息: {text_content}, 错误: {e}")
        # 失败时发送默认回复
        await api.send_message(1, group_id, message_id, "乌~啦啦啦～呀～哈")

