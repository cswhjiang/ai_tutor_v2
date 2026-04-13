import os
import zipfile
from pdfdeal import Doc2X


# import asyncio
# from pathlib import Path
# import json
# from playwright.async_api import async_playwright
#
# from typing import AsyncGenerator, List, Dict
# from typing_extensions import override
#
# from google.genai.types import Content
# from google.adk.agents import BaseAgent, LlmAgent
# from google.adk.agents.invocation_context import InvocationContext
# from google.adk.events import Event, EventActions
# from google.adk.tools import ToolContext
# from google.genai.types import Part, Blob
#
# from src.logger import logger
# from src.agents.experts.html_to_image.tool_v3 import html_to_image
# from src.utils import clean_json_string




def pdf_2_md(pdf_path: str, out_dir: str) -> str:
    client = Doc2X(apikey=os.getenv("DOC2X_API_KEY"), debug=False)
    pdf_path = os.path.abspath(pdf_path)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    succ, fail, has_error = client.pdf2file(
        pdf_file=pdf_path,
        output_path=out_dir,
        output_format="md_dollar",
    )
    if has_error or not succ or not succ[0]:
        raise RuntimeError(f"Doc2X 转换失败: {fail}")

    zip_path = os.path.join(out_dir, os.path.basename(succ[0]))
    if not os.path.isfile(zip_path):
        raise FileNotFoundError(f"Doc2X 返回的 zip 文件未找到: {zip_path}")

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)

    orig_base = os.path.splitext(os.path.basename(pdf_path))[0]
    md_file_name = next(
        f for f in os.listdir(out_dir)
        if f.endswith(".md") and os.path.isfile(os.path.join(out_dir, f))
    )
    new_md_file = f"{orig_base}.md"
    os.rename(
        os.path.join(out_dir, md_file_name),
        os.path.join(out_dir, new_md_file),
    )

    return os.path.join(out_dir, new_md_file)

pdf_2_md('./2507.13337v1.pdf', './md_files')