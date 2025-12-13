# 星露谷物语 QQ 机器人

一个基于 llbot 的 QQ 机器人，支持 AI 聊天、Wiki 查询、SMAPI 日志分析等功能。

## 功能特性

- 🤖 **AI 聊天**：基于 OpenAI API，支持自定义角色设定
- 📚 **Wiki 查询**：支持查询星露谷 Wiki，支持多种查询方式（wiki、查询、搜索）
- 🔍 **SMAPI 日志分析**：自动分析 SMAPI 日志链接，提供错误诊断和解决方案
- 👋 **入群欢迎**：自动欢迎新成员
- 📝 **日志记录**：完整的日志系统，支持按群组分类记录

## 项目结构

```
.
├── app.py              # 主入口文件
├── handlers.py         # 消息处理器
├── api.py              # WebSocket API 客户端
├── openai_client.py    # OpenAI 客户端封装
├── wiki.py             # Wiki 查询功能
├── smapi.py            # SMAPI 日志分析
├── logger.py           # 日志模块
├── config.json         # 配置文件
└── requirements.txt    # 依赖列表
```

## 环境要求

- Python 3.8+
- 已安装LLbot

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/Moitr/stardew_qq_wikibot.git
cd stardew_qq_wikibot
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 安装 Playwright 浏览器驱动

```bash
playwright install chromium
```

### 4. 配置 config.json

复制并编辑 `config.json` 文件，填入你的配置信息：

```json
{
    "ip": "your-websocket-server:port",
    "access_token": "your-access-token",
    "bot_user_id": "your-bot-user-id",
    "openai": {
        "api_key": "your-openai-api-key",
        "base_url": "your-openai-api-url"
    },
    "ai_chat": {
        "model": "deepseek-ai/DeepSeek-V3.2",
        "system_prompt": "你的系统提示词"
    },
    "ai_chat_smapi": {
        "model": "deepseek-ai/DeepSeek-R1",
        "system_prompt": "SMAPI 分析的系统提示词"
    },
    "wiki_rate_limit": {
        "max_queries": 2,
        "time_window": 45
    },
    "smapi_rate_limit": {
        "time_window": 600,
        "max_daily_uses": 20,
        "max_log_chars": 50000
    },
    "poke": {
        "enabled": true,
        "messages": [
            "消息1",
            "消息2"
        ]
    },
    "group_increase": {
        "enabled": true,
        "welcome_message": " 欢迎消息"
    }
}
```

## 使用方法

### 启动机器人

```bash
python app.py
```

### 功能使用

#### AI 聊天
- @机器人 + 消息内容：与机器人对话

#### Wiki 查询
- `.wiki <内容>` 或 `wiki <内容>`
- `查询 <内容>` 或 `搜索 <内容>`

#### SMAPI 日志分析
- 发送包含 `https://smapi.io/log/` 链接的消息
- 机器人会自动分析日志并提供解决方案

## 配置说明

### 主要配置项

- `ip`: WebSocket 服务器地址和端口
- `access_token`: WebSocket 访问令牌（可选）
- `bot_user_id`: 机器人 QQ 号
- `openai`: OpenAI API 配置（api_key 和 base_url 为公共配置）
- `ai_chat`: 普通聊天配置（model 和 system_prompt）
- `ai_chat_smapi`: SMAPI 日志分析配置（model 和 system_prompt）
- `wiki_rate_limit`: Wiki 查询频率限制
  - `max_queries`: 时间内最大查询次数
  - `time_window`: 时间（秒）
- `smapi_rate_limit`: SMAPI 日志分析频率限制
  - `time_window`: 用户+群组限制时间（秒），默认 600 秒（10分钟）
  - `max_daily_uses`: 全局每日最大使用次数，默认 20 次
  - `max_log_chars`: 日志内容最大字符数，默认 50000 字符
- `poke`: 戳一戳功能配置
  - `enabled`: 是否启用戳一戳功能，默认 `true`
  - `messages`: 戳一戳回复消息列表
- `group_increase`: 入群欢迎功能配置
  - `enabled`: 是否启用入群欢迎功能，默认 `true`
  - `welcome_message`: 欢迎消息内容

## 依赖说明

主要依赖包：

- `websockets`: WebSocket 客户端
- `openai`: OpenAI API 客户端
- `aiohttp`: 异步 HTTP 客户端
- `beautifulsoup4`: HTML 解析库
- `lxml`: XML/HTML 解析器
- `playwright`: 浏览器自动化库

## 日志系统

日志文件保存在 `logs/` 目录下：

- `global_errors_*.log`: 全局错误日志
- `group_*/messages_*.log`: 各群组消息日志
- `group_*/errors_*.log`: 各群组错误日志
- `wiki/wiki_*.log`: Wiki 查询日志
- `wiki/wiki_errors_*.log`: Wiki 错误日志
- `smapi/`: SMAPI 日志文件存储目录

## 注意事项

1. 确保 llbot开启WebSocket正向
2. 首次运行需要安装 Playwright 浏览器驱动

