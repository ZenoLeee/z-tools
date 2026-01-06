"""
彩色日志工具
支持不同级别的日志输出，带颜色和时间戳
"""
import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path


class ColorFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }

    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)

    def format(self, record):
        # 添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname:8}{self.COLORS['RESET']}"
        return super().format(record)


class Logger:
    """简单日志工具"""

    def __init__(self, name="z-tools", log_file=None):
        """
        初始化日志器

        Args:
            name: 日志器名称
            log_file: 日志文件路径（可选）
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 避免重复添加 handler
        if not self.logger.handlers:
            # 控制台 handler（彩色输出）
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)

            # 控制台格式：时间 模块:行数 级别 消息
            console_format = '%(asctime)s %(module)s:%(lineno)d %(levelname)s %(message)s'
            console_formatter = ColorFormatter(console_format, datefmt='%H:%M:%S')
            console_handler.setFormatter(console_formatter)

            self.logger.addHandler(console_handler)

            # 文件 handler（如果指定了文件）
            if log_file:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)

                # 文件格式（不带颜色）
                file_format = '%(asctime)s %(module)s:%(lineno)d %(levelname)s %(message)s'
                file_formatter = logging.Formatter(file_format, datefmt='%Y-%m-%d %H:%M:%S')
                file_handler.setFormatter(file_formatter)

                self.logger.addHandler(file_handler)

    def debug(self, msg, *args, **kwargs):
        """调试日志"""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """信息日志"""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """警告日志"""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """错误日志"""
        self.logger.error(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        """异常日志（自动包含堆栈信息）"""
        self.logger.error(msg, *args, **kwargs)
        self.logger.error(traceback.format_exc())


# 全局日志实例
_global_logger = None


def get_logger(name="z-tools", log_file=None):
    """
    获取日志器实例

    Args:
        name: 日志器名称
        log_file: 日志文件路径（可选）

    Returns:
        Logger 实例
    """
    global _global_logger

    if _global_logger is None:
        # 设置日志文件路径（如果未指定）
        if log_file is None:
            # 获取程序所在目录
            if getattr(sys, 'frozen', False):
                app_dir = Path(sys.executable).parent
            else:
                app_dir = Path(__file__).parent.parent

            log_file = app_dir / "z-tools.log"

        _global_logger = Logger(name, log_file)

    return _global_logger


# 便捷函数
def debug(msg, *args, **kwargs):
    """调试日志"""
    get_logger().debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    """信息日志"""
    get_logger().info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    """警告日志"""
    get_logger().warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    """错误日志"""
    get_logger().error(msg, *args, **kwargs)


def exception(msg, *args, **kwargs):
    """异常日志"""
    get_logger().exception(msg, *args, **kwargs)
