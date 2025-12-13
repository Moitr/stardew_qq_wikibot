import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import os
import asyncio
import uuid
import re
from logger import get_wiki_logger

url = "https://zh.stardewvalleywiki.com"

def clean_html_text(text):
	"""清理文本"""
	if not text:
		return ""
	# 清理多余的空格
	text = re.sub(r'\s+', ' ', text).strip()
	return text

async def Search(content):
	logger = get_wiki_logger()
	logger.info(f"开始搜索Wiki内容: {content}")
	
	SearchUrl = url + "/index.php?search=" + content
	try:
		async with aiohttp.ClientSession() as session:
			async with session.get(SearchUrl) as resp:
				SearchResult = await resp.text()
				final_url = str(resp.url)
	except Exception as e:
		logger.error(f"搜索请求失败 - 搜索内容: {content}, 错误: {e}")
		raise
	
	soup = BeautifulSoup(SearchResult, "lxml")
	title_elements = soup.find_all(class_="mw-search-result-heading")


	# 如果没有搜索结果，检查是否直接跳转到了条目页面
	if not title_elements:
		# 检查URL是否与搜索URL不同，说明发生了重定向
		if final_url != SearchUrl:
			page_title = soup.find(id="firstHeading")
			if page_title:
				title_text = page_title.get_text(strip=True)
				# 排除搜索结果页面的标题
				if title_text and "搜索结果" not in title_text and "Search results" not in title_text:
					# 从URL构建条目链接
					if '/index.php?title=' in final_url:
						title_param = final_url.split('title=')[1].split('&')[0]
						entry_url = url + "/index.php?title=" + title_param
					else:
						entry_url = final_url
					
					logger.info(f"搜索成功（直接匹配） - 搜索内容: {content}, 条目: {title_text}, URL: {entry_url}")
					infobox_text = await get_infobox_text(entry_url)
					return {
						'text': f"{infobox_text}\n更多信息：{entry_url}",
						'results': [{
							'title': title_text,
							'full_url': entry_url
						}],
						'type': 0
					}
		
		# 确实没有找到
		logger.info(f"搜索无结果 - 搜索内容: {content}")
		return {
			'text': f"乌啦啦，呀～没有找到与 '{content}' 相关的Wiki条目。",
			'results': [],
			'type': -1
		}

	results = []
	for element in title_elements:
		link_tag = element.find('a')
		title_text = link_tag.get_text(strip=True)
		href = link_tag.get('href')
		full_url = url + href if href.startswith('/') else href
		results.append({'title': title_text, 'full_url': full_url})

	formatted_lines = [f"{i}.{r['title']}" for i, r in enumerate(results, 1)]
	output_str = f"'{content}' 的搜索结果：" + '\n' + '\n'.join(formatted_lines)
	logger.info(f"搜索成功（多个结果） - 搜索内容: {content}, 结果数量: {len(results)}")
	return {
		'text': output_str,
		'results': results,
		'wiki_len':len(results),
		'type': 1
	}

async def get_infobox_text(full_url):
	try:
		async with aiohttp.ClientSession() as session:
			async with session.get(full_url) as resp:
				html_content = await resp.text()
	except Exception as e:
		logger = get_wiki_logger()
		logger.error(f"获取页面内容失败 - URL: {full_url}, 错误: {e}")
		return ""
	
	soup = BeautifulSoup(html_content, "lxml")
	description_meta = soup.find("meta", attrs={"name": "description"})
	description_text = ""
	if description_meta:
		description_content = description_meta.get("content", "")
		description_content = re.sub(r'data-sort-value=(?:\"|&quot;).*?(?:\"|&quot;)', '', description_content)
		description_soup = BeautifulSoup(description_content, "lxml")
		hidden_tags = description_soup.find_all(attrs={"style": re.compile(r"display\s*:\s*none", re.IGNORECASE)})
		for tag in hidden_tags:
			tag.decompose()

		# 提取纯文本并清理
		description_text = clean_html_text(description_soup.get_text(separator=" ", strip=False))
	infobox = soup.find(id="infoboxborder")
	
	# 如果找不到 infobox，直接返回 description_text
	if not infobox:
		return f"ő {description_text}" if description_text else ""
	
	infobox_data = {}
	infobox_title = ""
	header = infobox.find(id="infoboxheader")
	if header:
		infobox_title = header.get_text(strip=True)
	rows = infobox.find_all("tr")
	for row in rows:
		section = row.find(id="infoboxsection")
		detail = row.find(id="infoboxdetail")
		if section and detail:
			section_text = section.get_text(strip=True)
			
			# 在提取文本前，将图片标签替换为空格，避免数字连在一起
			# 创建一个副本以避免修改原始元素
			detail_copy = BeautifulSoup(str(detail), "lxml")
			
			# 删除所有 style="display: none;" 的隐藏标签（如 data-sort-value）
			hidden_tags = detail_copy.find_all(attrs={"style": re.compile(r"display\s*:\s*none", re.IGNORECASE)})
			for tag in hidden_tags:
				tag.decompose()  # 完全删除标签及其内容
			
			images = detail_copy.find_all("img")
			for img in images:
				# 将图片标签替换为空格
				img.replace_with(" ")
			
			# 提取所有文本内容（包括链接内的和链接外的）
			# 先获取所有文本节点和链接
			detail_text = detail_copy.get_text(separator=" ", strip=False)
			
			# 清理多余的空格，但保留数字之间的空格
			# 将多个连续空格替换为单个空格
			detail_text = re.sub(r'\s+', ' ', detail_text).strip()
			
			if section_text and detail_text:
				infobox_data[section_text] = detail_text
	
	infobox_lines = []
	if infobox_title:
		infobox_lines.append(f"{infobox_title}")
		if description_text:
			infobox_lines.append(f"ő {description_text}")
	infobox_lines.extend([f"• {k}：{v}" for k, v in infobox_data.items()])
	return "\n".join(infobox_lines)


async def SearchResult(full_url):
	logger = get_wiki_logger()
	logger.info(f"开始截图Wiki页面: {full_url}")
	
	ERROR_CODE = -1
	
	async def _take_screenshot():
		screenshot_dir = "screenshots"
		if not os.path.exists(screenshot_dir):
			os.makedirs(screenshot_dir)
		
		# 使用 UUID
		unique_id = str(uuid.uuid4())
		screenshot_path = os.path.join(screenshot_dir, f"{unique_id}.png")
		
		async with async_playwright() as p:
			browser = await p.chromium.launch(headless=True)
			
			mobile_device = {
				"viewport": {"width": 430, "height": 932},
				"user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
				"device_scale_factor": 3,
				"is_mobile": True,
				"has_touch": True
			}
			
			context = await browser.new_context(**mobile_device)
			page = await context.new_page()
			
			try:
				try:
					await page.goto(full_url, wait_until="load", timeout=60000)
					logger.info(f"页面加载成功: {full_url}")
				except Exception as e:
					logger.error(f"页面加载超时，尝试继续 - URL: {full_url}, 错误: {e}")
					print(f"页面加载超时，尝试继续: {e}")
				
				# 等待 DOM 内容加载
				try:
					await page.wait_for_load_state("domcontentloaded", timeout=20000)
				except:
					pass
				
				# 等待元素渲染完成
				await asyncio.sleep(1)
				
				# 查找并截图 infoboxborder 元素
				infobox_element = page.locator('#infoboxborder')
				# 检查元素是否存在
				if await infobox_element.count() == 0:
					logger.warning(f"未找到 infoboxborder 元素 - URL: {full_url}")
					return ERROR_CODE
				
				# 等待元素可见
				try:
					await infobox_element.wait_for(state='visible', timeout=20000)
				except Exception as e:
					logger.warning(f"infoboxborder 元素等待可见超时 - URL: {full_url}, 错误: {e}")
					return ERROR_CODE
				
				await infobox_element.screenshot(path=screenshot_path, timeout=60000)
				logger.info(f"截图成功 - URL: {full_url}, 保存路径: {screenshot_path}")
			finally:
				await browser.close()
		
		return os.path.abspath(screenshot_path)
	
	try:
		# 设置总体超时为 60 秒，防止整个流程卡死
		result = await asyncio.wait_for(_take_screenshot(), timeout=60.0)
		logger.info(f"截图操作完成 - URL: {full_url}, 结果: {result}")
		return result
	except asyncio.TimeoutError:
		logger.error(f"截图操作总体超时（60秒） - URL: {full_url}")
		print(f"截图操作总体超时（60秒）")
		return ERROR_CODE
	except Exception as e:
		logger.error(f"截图失败 - URL: {full_url}, 错误类型: {type(e).__name__}, 错误信息: {str(e)}")
		import traceback
		logger.error(f"截图失败详细错误 - URL: {full_url}\n{traceback.format_exc()}")
		print(f"截图失败: {type(e).__name__}: {str(e)}")
		traceback.print_exc()
		return ERROR_CODE
