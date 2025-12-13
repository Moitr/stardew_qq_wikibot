import logging
import os
from datetime import datetime
from pathlib import Path

# ANSI颜色代码
class Colors:
    RESET = '\033[0m'
    INFO = '\033[96m'
    ERROR = '\033[91m'

# 日志过滤器
class LevelFilter(logging.Filter):
    def __init__(self, level):
        super().__init__()
        self.level = level
    
    def filter(self, record):
        return record.levelno == self.level

# 在Windows上启用ANSI转义码支持
if os.name == 'nt':
    os.system('')

# 创建日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 存储已创建的日志记录器
loggers = {}
global_error_logger = None
wiki_logger = None

def get_global_error_logger():
    """获取全局错误日志记录器"""
    global global_error_logger
    if global_error_logger is None:
        logger = logging.getLogger("global_errors")
        logger.setLevel(logging.ERROR)
        
        if not logger.handlers:
            today = datetime.now().strftime("%Y-%m-%d")
            error_handler = logging.FileHandler(
                LOG_DIR / f"global_errors_{today}.log",
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            error_handler.setFormatter(error_formatter)
            logger.addHandler(error_handler)
        
        global_error_logger = logger
    
    return global_error_logger

def get_group_logger(group_id):
    """为指定群号获取或创建日志记录器"""
    if group_id not in loggers:
        # 为每个群创建单独的日志目录
        group_log_dir = LOG_DIR / f"group_{group_id}"
        group_log_dir.mkdir(exist_ok=True)
        
        # 创建日志记录器
        logger = logging.getLogger(f"group_{group_id}")
        logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not logger.handlers:
            # 消息日志文件（按日期）- 只记录INFO级别
            today = datetime.now().strftime("%Y-%m-%d")
            message_handler = logging.FileHandler(
                group_log_dir / f"messages_{today}.log",
                encoding='utf-8'
            )
            message_handler.setLevel(logging.INFO)
            # 添加过滤器，只允许INFO级别的日志
            message_handler.addFilter(LevelFilter(logging.INFO))
            message_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            message_handler.setFormatter(message_formatter)
            logger.addHandler(message_handler)
            
            # 错误日志文件（按日期）- 只记录ERROR级别
            error_handler = logging.FileHandler(
                group_log_dir / f"errors_{today}.log",
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            error_handler.setFormatter(error_formatter)
            logger.addHandler(error_handler)
        
        loggers[group_id] = logger
    
    return loggers[group_id]

def get_wiki_logger():
    """获取Wiki日志记录器"""
    global wiki_logger
    if wiki_logger is None:
        logger = logging.getLogger("wiki")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # 创建wiki日志目录
            wiki_log_dir = LOG_DIR / "wiki"
            wiki_log_dir.mkdir(exist_ok=True)
            
            # Wiki日志文件（按日期）
            today = datetime.now().strftime("%Y-%m-%d")
            wiki_handler = logging.FileHandler(
                wiki_log_dir / f"wiki_{today}.log",
                encoding='utf-8'
            )
            wiki_handler.setLevel(logging.INFO)
            wiki_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            wiki_handler.setFormatter(wiki_formatter)
            logger.addHandler(wiki_handler)
            
            # Wiki错误日志文件（按日期）
            wiki_error_handler = logging.FileHandler(
                wiki_log_dir / f"wiki_errors_{today}.log",
                encoding='utf-8'
            )
            wiki_error_handler.setLevel(logging.ERROR)
            wiki_error_handler.addFilter(LevelFilter(logging.ERROR))
            wiki_error_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            wiki_error_handler.setFormatter(wiki_error_formatter)
            logger.addHandler(wiki_error_handler)
        
        wiki_logger = logger
    
    return wiki_logger

