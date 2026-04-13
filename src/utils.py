import os
import re
import base64
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional
import random
import time
from typing import Awaitable, Callable, Optional, TypeVar, ByteString
import sqlite3

from sqlalchemy.exc import OperationalError as SAOperationalError
import asyncio
from pydantic import BaseModel


from src.logger import logger
from conf.system import SYS_CONFIG


def is_valid_url(url_string: str) -> bool:
    """检查给定的字符串是否是有效的URL。"""
    if not url_string or not isinstance(url_string, str):
        return False
    try:
        result = urlparse(url_string)
        # 确保有协议（如http）和网络位置（如example.com）
        return all([result.scheme, result.netloc])
    except (ValueError, AttributeError):
        return False


def create_file_protocol_url(local_path_str: str) -> str:
    """
    根据操作系统将本地文件路径转换为 'file://' 格式的URL。
    这是为了兼容需要此格式的API（如DashScope SDK）。
    """

    if not local_path_str or not isinstance(local_path_str, str):
        logger.warning(f"接收到无效的本地路径进行转换: {local_path_str}")
        return ""

    path_obj = Path(local_path_str)

    # 如果路径不是绝对路径，则相对于项目根目录解析它
    if not path_obj.is_absolute():
        #path_obj = Path(SYS_CONFIG.base_dir)
        path_obj = Path(SYS_CONFIG.base_dir)/path_obj


    # 确保文件存在
    if not path_obj.is_file():
        logger.error(f"文件在路径 '{path_obj}' 未找到，无法创建file:// URL。")
        return ""

    # 根据操作系统格式化路径
    if os.name == "nt":  # Windows系统
        # Windows路径格式: file:///C:/path/to/file
        #return "file:///" + str(path_obj).replace("\\", "/")
        return "file://" + str(path_obj).replace("\\", "/")
    else:  # macOS, Linux等
        # POSIX路径格式: file:///path/to/file
        return "file://" + str(path_obj)
    

def binary_to_base64(image_binary: ByteString, image_format:str = 'image/png', with_head:bool=True) -> str:
    encoded_string = base64.b64encode(image_binary).decode('utf-8')
    if with_head:
        return f"data:{image_format};base64,{encoded_string}"
    else:
        return encoded_string

_JSON_FENCE_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def clean_json_string(s: str) -> str:
    """
    从字符串中提取第一个 ```json ... ``` 代码块中的内容。
    若不存在该代码块，则返回原字符串去除首尾空白后的结果。
    """
    if not s:
        return ""

    m = _JSON_FENCE_RE.search(s)
    if m:
        return m.group(1).strip()

    # 没有 ```json``` 包裹时：退化为简单 strip
    return s.strip('`')


T = TypeVar("T")

# 常见的 SQLite 锁/忙错误
_RETRYABLE_SQLITE_TOKENS = (
    "database is locked",
    "database table is locked",
    "database schema is locked",
    "database is busy",
    "sqlite_busy",
)

def _is_retryable_sqlite_error(exc: BaseException) -> bool:
    """
    判断异常是否属于 SQLite 锁/忙导致的可重试错误。
    - 兼容 SQLAlchemy 的 OperationalError 包装（.orig）
    - 兼容 aiosqlite / sqlite3 的 OperationalError
    - 使用 message 兜底判断（部分情况下错误类型会被包裹）
    """
    root = exc

    # SQLAlchemy 的 OperationalError 通常携带原始异常在 .orig
    if isinstance(exc, SAOperationalError) and getattr(exc, "orig", None):
        root = exc.orig

    # 展开 __cause__（可能被再次包裹）
    while getattr(root, "__cause__", None) is not None:
        root = root.__cause__

    # 明确的 sqlite3.OperationalError
    if isinstance(root, sqlite3.OperationalError):
        msg = str(root).lower()
        return any(token in msg for token in _RETRYABLE_SQLITE_TOKENS)

    # 兜底：直接用异常消息判断
    msg = str(exc).lower()
    return any(token in msg for token in _RETRYABLE_SQLITE_TOKENS)


async def database_op_with_retry(
    op: Callable[..., Awaitable[T]],
    *,
    retries: int = 5,
    base_delay: float = 0.05,
    max_delay: float = 1.0,
    jitter: float = 0.2,
    max_elapsed: float = 3.0,
    logger: Optional[object] = None,
    op_name: str = "sqlite_write",
    **kwargs
) -> T:
    """
    针对 Database 操作的重试包装器。

    参数说明：
    - op: 实际要执行的 async 操作（例如 session_service.append_event）
    - retries: 最多重试次数（不含首次尝试）
    - base_delay: 首次退避延迟（秒）
    - max_delay: 单次退避延迟上限（秒）
    - jitter: 抖动比例（0.2 表示 ±20% 抖动，减少并发争抢）
    - max_elapsed: 总耗时上限（秒），超过则直接抛错
    - logger: 可选日志对象
    - op_name: 操作名，便于日志定位
    """
    start = time.monotonic()
    attempt = 0
    while True:
        try:
            return await op(**kwargs)

        # 取消必须立即抛出，避免吞掉取消信号
        except asyncio.CancelledError:
            raise

        except Exception as exc:
            # 非锁/忙错误直接抛出
            if not _is_retryable_sqlite_error(exc):
                raise

            attempt += 1
            elapsed = time.monotonic() - start

            # 达到重试上限或超时，则抛出原异常
            if attempt > retries or elapsed >= max_elapsed:
                raise

            # 指数退避：base * 2^(attempt-1)，并限制上限
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)

            # 抖动：避免多个协程同时醒来争抢锁
            if jitter > 0:
                delay = delay * (1 + random.uniform(-jitter, jitter))

            if logger:
                logger.warning(
                    f"{op_name} hit SQLite lock/busy, retrying "
                    f"(attempt={attempt}/{retries}, delay={delay:.3f}s, elapsed={elapsed:.3f}s): {exc}"
                )

            # 等待后重试
            await asyncio.sleep(max(delay, 0.0))


# def clean_json_string(json_string):
#     index_1 = json_string.find('```json')
#     if index_1 >=0:
#         json_string = json_string[index_1:]
#     index_2 = json_string.find('```', 3)
#     if index_2 >= 0:
#         json_string = json_string[:index_2+3]
#     pattern = r'^```json\s*(.*?)\s*```$'
#     cleaned_string = re.sub(pattern, r'\1', json_string, flags=re.DOTALL)
#     return cleaned_string.strip()

# def clean_json_string(s: str) -> str:
#     """
#     清理来自LLM的字符串，使其可以被 json.loads() 成功解析。
#
#     处理步骤包括：
#     1. 提取最外层的JSON结构（处理Markdown代码块和额外文本）。
#     2. 移除尾随的逗号 (e.g., {"key": "value",})。
#     3. 修复未用双引号括起来的键名。
#     4. 移除/修复特殊字符和不标准的转义。
#
#     Args:
#         s: 来自LLM的原始字符串。
#
#     Returns:
#         一个尽可能符合标准的 JSON 字符串。
#     """
#
#     # --- 1. 提取最外层的JSON结构 ---
#     # 查找并提取位于 ```json ... ```, ``` ... ```, 或直接是 {...} 或 [...] 的内容
#     match = re.search(r"```json\s*(\{.*\}|\[.*\])\s*```", s, re.DOTALL)
#     if not match:
#         match = re.search(r"```\s*(\{.*\}|\[.*\])\s*```", s, re.DOTALL)
#
#     if match:
#         # 如果找到了代码块，使用代码块中的内容
#         cleaned_s = match.group(1).strip()
#     else:
#         # 否则，尝试找到第一个 { 或 [ 到最后一个 } 或 ] 之间的内容
#         start = s.find('{') if s.find('{') != -1 else s.find('[')
#         end = s.rfind('}') if s.rfind('}') != -1 else s.rfind(']')
#
#         if start != -1 and end != -1 and end > start:
#             # 找到最外层的 JSON 结构
#             cleaned_s = s[start:end + 1].strip()
#         else:
#             # 如果找不到明显的 JSON 结构，返回原始字符串，让后续步骤处理或让 json.loads 失败
#             cleaned_s = s.strip()
#
#     # --- 2. 移除尾随的逗号 (e.g., {"a": 1, "b": 2,}) ---
#     # 这是一个常见的非标准 JSON 问题
#     # 它会移除在 } 或 ] 之前的逗号，通常发生在最后一个元素之后
#     cleaned_s = re.sub(r',\s*([}\]])', r'\1', cleaned_s)
#
#     # --- 3. 修复未用双引号括起来的键名 ---
#     # 查找所有被单引号括起来的键名或不被引号括起来的键名（紧跟冒号前的单词）
#     # 并将其替换为双引号括起来。
#     # [a-zA-Z0-9_]+ 是一个简化，它假设键名由字母、数字和下划线组成。
#     # 注意: 这一步有风险，但在LLM输出中很实用。
#     cleaned_s = re.sub(r'([\{\,]\s*)(\'[^\']+\')\s*:', r'\1\2:', cleaned_s)  # 处理单引号键名
#     # 处理未引用的键名 (e.g., {key: "value"})
#     cleaned_s = re.sub(r'([\{\,]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', cleaned_s)
#
#     # --- 4. 修复单引号字符串值为双引号 (可选，但常用) ---
#     # 查找非键名的字符串（即不在冒号前的字符串）并替换引号
#     # 这一步比较复杂且容易误伤，建议只在确认有这个问题时再启用。
#     # cleaned_s = cleaned_s.replace("'", '"')
#
#     # 修复常见的不标准转义，如 \t, \n (如果它们是意外出现的)
#     # 移除非法的控制字符（通常不需要，但作为一个安全网）
#     cleaned_s = cleaned_s.replace('\\\\', '\\')
#     cleaned_s = cleaned_s.replace('\\\n', '')  # 移除行尾的转义换行
#
#     return cleaned_s


# gemini的结果
# def clean_json_string(s: str) -> str:
#     """
#     清理来自LLM的字符串，使其可以被 json.loads() 成功解析。
#
#     处理步骤包括：
#     1. 提取最外层的JSON结构（处理Markdown代码块和额外文本）。
#     2. 移除尾随的逗号 (e.g., {"key": "value",})。
#     3. 修复未用双引号括起来的键名（包括单引号括起来的键名）。
#     4. 移除/修复不标准的转义（只保留安全的修复）。
#
#     Args:
#         s: 来自LLM的原始字符串。
#
#     Returns:
#         一个尽可能符合标准的 JSON 字符串。
#     """
#     if not s:
#         return ""
#
#     # --- 1. 提取最外层的JSON结构 ---
#
#     # 查找并提取位于 ```json ... ``` 或 ``` ... ``` 的内容
#     match: Optional[re.Match] = re.search(r"```json\s*(\{.*\}|\[.*\])\s*```", s, re.DOTALL)
#     if not match:
#         match = re.search(r"```\s*(\{.*\}|\[.*\])\s*```", s, re.DOTALL)
#
#     if match:
#         # 如果找到了代码块，使用代码块中的内容
#         cleaned_s = match.group(1).strip()
#     else:
#         # 否则，尝试找到第一个 { 或 [ 到最后一个 } 或 ] 之间的内容
#         start = s.find('{') if s.find('{') != -1 else s.find('[')
#         end = s.rfind('}') if s.rfind('}') != -1 else s.rfind(']')
#
#         if start != -1 and end != -1 and end > start:
#             # 找到最外层的 JSON 结构
#             cleaned_s = s[start:end + 1].strip()
#         else:
#             # 如果找不到明显的 JSON 结构，返回原始字符串，让后续步骤处理或让 json.loads 失败
#             cleaned_s = s.strip()
#
#     # --- 2. 移除尾随的逗号 (e.g., {"a": 1, "b": 2,}) ---
#     # 这是一个常见的非标准 JSON 问题
#     # 它会移除在 } 或 ] 之前的逗号，通常发生在最后一个元素之后
#     cleaned_s = re.sub(r',\s*([}\]])', r'\1', cleaned_s)
#
#     # --- 3. 修复未用双引号括起来的键名 ---
#
#     # 3a. 处理单引号键名 (e.g., {'key': "value"}) 并转为双引号
#     # (\'[^\']+\') 匹配被单引号括起来的任意字符串
#     cleaned_s = re.sub(r'([\{\,]\s*)(\'[^\']+\')\s*:',
#                        lambda m: f'{m.group(1)}"{m.group(2).strip("\'")}"',
#                        cleaned_s)
#
#     # 3b. 处理未引用的键名 (e.g., {key: "value"})
#     # 使用更宽泛的字符集，例如 [a-zA-Z0-9_-] 来兼容常见键名格式
#     cleaned_s = re.sub(r'([\{\,]\s*)([a-zA-Z0-9_-]+)\s*:', r'\1"\2":', cleaned_s)
#
#     # --- 4. 修复/移除不标准的转义 ---
#
#     # 移除行尾的转义换行 (例如，LLM为了格式化而引入的 \n)
#     cleaned_s = cleaned_s.replace('\\\n', '')
#
#     # 【重要修复】：移除潜在危险的代码。
#     # 原始代码中的 cleaned_s.replace('\\\\', '\\') 会破坏合法的 JSON 路径转义，故移除。
#
#     return cleaned_s

# ----------------------------------------------------
# 导入 json 模块只是为了方便测试，并不是函数运行所必须的
# import json
# # 示例测试:
# raw_s = 'Sure, here is the JSON result: ```json\n{\n  "name": "Gemini",\n  "type": "AI",\n  "status": "active",\n  "data": {\n    "key1": 123,\n    "key2": "abc",\n  }\n}\n```\n'
# clean_s = clean_json_string(raw_s)
# print(clean_s)
# # print(json.loads(clean_s))





# chatgpt 的结果
# def clean_json_string(s: str) -> str:
#     """
#     清理来自LLM的字符串，使其可以被 json.loads() 成功解析。
#
#     处理步骤包括：
#     1. 提取最外层的JSON结构（处理Markdown代码块和额外文本）。
#     2. 移除尾随的逗号 (e.g., {"key": "value",})。
#     3. 修复未用双引号括起来的键名（包括单引号键名、裸键名）。
#     4. 对少量常见的非法换行做修复。
#
#     Args:
#         s: 来自LLM的原始字符串。
#
#     Returns:
#         一个尽可能符合标准的 JSON 字符串。
#     """
#
#     # --- 1. 提取最外层的JSON结构 ---
#     # 使用 *非贪婪* 的匹配，避免吃到太多内容
#     match = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", s, re.DOTALL)
#     if not match:
#         match = re.search(r"```\s*(\{.*?\}|\[.*?\])\s*```", s, re.DOTALL)
#
#     if match:
#         # 如果找到了代码块，使用代码块中的内容
#         cleaned_s = match.group(1).strip()
#     else:
#         # 否则，尝试找到第一个 { 或 [ 到最后一个 } 或 ] 之间的内容
#         brace_pos = s.find('{')
#         bracket_pos = s.find('[')
#
#         if brace_pos == -1 and bracket_pos == -1:
#             start = -1
#         elif brace_pos == -1:
#             start = bracket_pos
#         elif bracket_pos == -1:
#             start = brace_pos
#         else:
#             start = min(brace_pos, bracket_pos)
#
#         end_brace = s.rfind('}')
#         end_bracket = s.rfind(']')
#
#         if end_brace == -1 and end_bracket == -1:
#             end = -1
#         elif end_brace == -1:
#             end = end_bracket
#         elif end_bracket == -1:
#             end = end_brace
#         else:
#             end = max(end_brace, end_bracket)
#
#         if start != -1 and end != -1 and end > start:
#             cleaned_s = s[start:end + 1].strip()
#         else:
#             cleaned_s = s.strip()
#
#     # --- 2. 移除尾随的逗号 (e.g., {"a": 1, "b": 2,}) ---
#     # 注意：这是全局替换，有一定“误伤”风险，只适合 LLM 输出这种场景
#     cleaned_s = re.sub(r',\s*([}\]])', r'\1', cleaned_s)
#
#     # --- 3. 修复键名 ---
#
#     # 3.1 单引号键名：{'key': 1} -> {"key": 1}
#     # ✅ 修正点：原代码只是原样替换，这里明确把单引号换成双引号
#     cleaned_s = re.sub(
#         r'([\{,]\s*)\'([^\'"]+)\'\s*:',
#         r'\1"\2":',
#         cleaned_s,
#     )
#
#     # 3.2 裸键名：{key: 1} -> {"key": 1}
#     # 限制首字符为字母或下划线，避免把数字等误当成键名
#     cleaned_s = re.sub(
#         r'([\{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:',
#         r'\1"\2":',
#         cleaned_s,
#     )
#
#     # --- 4. 处理一些常见“断行转义”的情况 ---
#     # 只处理 "\<换行>" 这种人工拼出来的续行，不再动合法的 "\\" 序列
#     # ✅ 修正点：删除了原来的 cleaned_s.replace('\\\\', '\\')
#     cleaned_s = re.sub(r'\\\s*\n\s*', '', cleaned_s)
#
#     return cleaned_s
