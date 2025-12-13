import aiohttp
import asyncio
import re
import json
import os


async def check_log_parse_error(url: str) -> str | None:
    """
    检查 smapi.io/log 链接页面中是否包含 "couldn't parse that log" 错误信息
    如果没有错误，提取并保存RawText到logs/smapi/目录
    
    Args:
        url: smapi.io/log 链接
        
    Returns:
        str | None: 如果保存了文件返回文件路径，如果有错误返回None
    """
    try:
        # 设置模拟浏览器的请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                
                # 从JavaScript中提取fetchUri
                fetch_uri_pattern = r'fetchUri:\s*"([^"]+)"'
                match = re.search(fetch_uri_pattern, html)
                
                if match:
                    fetch_uri = match.group(1)
                    
                    # 延迟几秒后再请求JSON数据
                    await asyncio.sleep(3)
                    
                    # 请求JSON数据
                    async with session.get(fetch_uri, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as json_response:
                        if json_response.status == 200:
                            json_data = await json_response.json()
                            
                            # 检查Error字段
                            if 'Error' in json_data and json_data['Error']:
                                error_text = str(json_data['Error']).lower()
                                target_text = "couldn't parse that log"
                                if target_text in error_text:
                                    return None  # 有错误，返回None
                                return None
                            else:
                                # 没有错误，提取RawText并保存
                                if 'RawText' in json_data and json_data['RawText']:
                                    # 创建logs/smapi目录（如果不存在）
                                    save_dir = 'logs/smapi'
                                    os.makedirs(save_dir, exist_ok=True)
                                    
                                    # 从URL中提取log ID作为文件名
                                    log_id_match = re.search(r'/log/([a-f0-9]+)', url)
                                    if log_id_match:
                                        log_id = log_id_match.group(1)
                                        filename = f'smapi_log_{log_id}.txt'
                                    else:
                                        filename = 'smapi_log.txt'
                                    
                                    filepath = os.path.join(save_dir, filename)
                                    
                                    # 去掉多余的空格：去除行尾空格和制表符，并过滤TRACE、INFO和DEBUG等级的日志
                                    raw_text = json_data['RawText']
                                    # 按行处理，去除每行末尾的空格和制表符，并过滤TRACE、INFO和DEBUG等级的日志
                                    lines = raw_text.split('\n')
                                    filtered_lines = [line.rstrip() for line in lines if 'TRACE' not in line and 'INFO' not in line and 'DEBUG' not in line]
                                    # 去掉多余的换行（连续的空行）
                                    cleaned_lines = []
                                    prev_empty = False
                                    for line in filtered_lines:
                                        if line == '':
                                            if not prev_empty:
                                                cleaned_lines.append(line)
                                            prev_empty = True
                                        else:
                                            cleaned_lines.append(line)
                                            prev_empty = False
                                    cleaned_text = '\n'.join(cleaned_lines)
                                    
                                    # 提取标题信息字段
                                    title_info = []
                                    fields_to_extract = ['IsSplitScreen', 'GamePath', 'OperatingSystem', 'GameVersion']
                                    
                                    for field in fields_to_extract:
                                        if field in json_data and json_data[field] is not None:
                                            value = str(json_data[field])
                                            title_info.append(f"{field}: {value}")
                                    
                                    # 写入文件：先写RawText，再追加标题信息
                                    with open(filepath, 'w', encoding='utf-8') as f:
                                        f.write(cleaned_text)
                                        if title_info:
                                            f.write('\n\n')
                                            for info in title_info:
                                                f.write(info + '\n')
                                    
                                    return filepath
                                
                                return None
                        else:
                            return None
                else:
                    return None
                
    except asyncio.TimeoutError:
        return None
    except Exception as e:
        return None


