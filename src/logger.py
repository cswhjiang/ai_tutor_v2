import sys
import time
from loguru import logger
from conf.system import SYS_CONFIG
from conf.path import LOGS_ROOT
from pathlib import Path

from src.context import username_context


def setup_logger() -> None:
    """
    Sets up the loguru logger with configured settings.
    Logs will be output to both console and a file.
    """
    # 确保日志目录存在
    log_dir = Path(LOGS_ROOT)
    log_dir.mkdir(exist_ok=True)

    # 从配置中获取日志文件名模板
    log_file_template = SYS_CONFIG.log_file
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    log_file_path = log_dir / log_file_template.format(time=timestamp)

    # 移除默认的处理器，以便完全自定义
    logger.remove()

    logger.configure(patcher=lambda record: record.update(context=username_context.get()))

    # 添加控制台处理器
    logger.add(
        sys.stderr,
        level=SYS_CONFIG.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<blue>username: {context: <10}</blue> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # 添加文件处理器
    logger.add(
        log_file_path,
        level=SYS_CONFIG.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | username: {context: <10} | {name}:{function}:{line} - {message}",
        rotation=SYS_CONFIG.rotation,
        retention=SYS_CONFIG.retention,
        compression="zip",
        encoding="utf-8",
        serialize=False,
        backtrace=True,
        diagnose=True,
    )

    logger.info("日志系统初始化完成。")
    logger.debug(f"日志级别设置为: {SYS_CONFIG.log_level}")
    logger.debug(f"日志文件将保存在: {log_file_path}，使用模板: {log_file_template}")


# 在模块加载时就配置好 logger
setup_logger()

# 导出 logger 实例供其他模块使用
__all__ = ["logger"]
