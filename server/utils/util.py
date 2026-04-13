import time, json, re, shutil
from datetime import datetime
from fastapi import UploadFile
from typing import Dict, Any, Optional
import os

from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import base64
import mimetypes

from google.genai.types import Part, Blob
from src.logger import logger

# --- Pydantic 模型定义 ---
class SessionCreateResponse(BaseModel):
    user_id: str
    session_id: str
    message: str

class LoginRequest(BaseModel):
    username: str
    password: str

class VerifyRequest(BaseModel):
    token: str


# --- 辅助函数 ---
def clean_and_parse_json(json_string: str) -> Dict[str, Any]:
    cleaned_string = re.sub(
        r"^```(json)?\s*|\s*```$", "", json_string.strip(), flags=re.MULTILINE
    )
    try:
        return json.loads(cleaned_string)
    except json.JSONDecodeError:
        logger.error(f"JSON解析失败，原始字符串: '{json_string}'")
        return {}


def save_upload_file_sync(upload_file: UploadFile, uploads_dir: Path) -> str:
    """
    同步保存上传的文件并返回其绝对路径。
    在调用此函数时，必须确保 upload_file.file 仍然是打开的。
    """
    try:
        timestamp = time.strftime("%Y%m%d%H%M%S")
        safe_filename = re.sub(r"[^\w\.\-]", "_", upload_file.filename)  # type: ignore
        file_location = os.path.join(uploads_dir, f"{timestamp}_{safe_filename}")

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        logger.info(f"上传文件已同步保存: {file_location}")
        return file_location
    except Exception as e:
        logger.error(f"同步保存上传文件失败: {e}", exc_info=True)
        return ""
    finally:
        upload_file.file.close()


# def save_upload_image(image1: Optional[UploadFile], image2: Optional[UploadFile], uploads_dir: Path) -> None:
#     img1_path = save_upload_file_sync(image1, uploads_dir) if image1 and image1.filename else None
#     img2_path = save_upload_file_sync(image2, uploads_dir) if image2 and image2.filename else None
#
#     return img1_path, img2_path


# def load_png_as_part(file_path)->Part:
#     with open(file_path, 'rb') as f:
#         img_binary = f.read()
#
#     return Part(inline_data=Blob(mime_type='image/png', data=img_binary))
#
# # 将文件 load 为 Part
# def load_document_as_part(file_path: str) -> Part:
#     """
#     将 PDF, TXT, DOCX 等文档加载为 Part 对象。
#     支持自动识别 MIME 类型。
#     """
#     path = Path(file_path)
#
#     # 1. 自动获取 MIME 类型
#     # 如果无法识别，则根据后缀名手动映射常见文档类型
#     mime_type, _ = mimetypes.guess_type(file_path)
#     if not mime_type:
#         extension = path.suffix.lower()
#         mime_map = {
#             '.pdf': 'application/pdf',
#             '.txt': 'text/plain',
#             '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
#             '.doc': 'application/msword',
#         }
#         mime_type = mime_map.get(extension, 'application/octet-stream')
#
#     # 2. 以二进制模式读取文件内容
#     with open(file_path, 'rb') as f:
#         file_binary = f.read()
#
#     # 3. 返回构造的 Part 对象
#     return Part(inline_data=Blob(mime_type=mime_type, data=file_binary))


def load_file_as_part(file_path: str) -> "Part":
    """
    将任意文件（图像、视频、音频、文档等）加载为 Part 对象。
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"未找到文件: {file_path}")

    # 1. 自动获取 MIME 类型
    # mimetypes.guess_type 能识别大多数标准文件格式（jpg, mp4, pdf, csv 等）
    mime_type, _ = mimetypes.guess_type(file_path)

    # 2. 兜底处理：如果无法识别，根据后缀名补充或设为二进制流
    if not mime_type:
        extension = path.suffix.lower()
        # 补充一些 mimetypes 库可能缺失的常见类型
        extra_mime_map = {
            '.json': 'application/json',
            '.md': 'text/markdown',
            '.csv': 'text/csv',
            '.py': 'text/x-python',
        }
        mime_type = extra_mime_map.get(extension, 'application/octet-stream')

    # 3. 以二进制模式读取文件内容
    # 对于多模态模型，无论是图片还是视频，底层逻辑都是读取其二进制字节流
    with open(file_path, 'rb') as f:
        file_binary = f.read()

    # 4. 返回构造的 Part 对象
    return Part(inline_data=Blob(mime_type=mime_type, data=file_binary))


def format_sse_event(data: Dict[str, Any]) -> str:
    json_data = json.dumps(data, ensure_ascii=False)
    return f"data: {json_data}\n\n"

def current_time_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def encode_media(file_path: str):
    # 自动检测 MIME 类型（根据文件扩展名）
    logger.info(file_path)
    if file_path is None:
        return None

    mime_type, _ = mimetypes.guess_type(file_path)

    # 如果无法识别，就默认设为二进制流
    if mime_type is None:
        mime_type = "application/octet-stream"

    # 读取文件内容并编码
    with open(file_path, 'rb') as f:
        file_content = f.read()

    # 生成 Base64 数据 URI
    base64_data = base64.b64encode(file_content).decode('utf-8')
    return f"data:{mime_type};base64,{base64_data}"


