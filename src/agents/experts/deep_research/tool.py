
import httpx
from typing import Any
import requests
from bs4 import BeautifulSoup
import trafilatura

from dashscope import ImageSynthesis
from google.adk.tools import ToolContext
from google.adk.events import Event, EventActions
from google.genai.types import Part
from google.genai.types import Content
from asyncddgs import aDDGS

from conf.system import SYS_CONFIG
from conf.api import API_CONFIG
from src.logger import logger


def get_text_from_url(url: str):
    downloaded = trafilatura.fetch_url(url)
    return trafilatura.extract(downloaded) if downloaded else None


# def get_text_from_url(url: str) -> str:
#     """
#     Input a URL and return all visible text content from that web page.
#     """
#     try:
#         # Send the HTTP request
#         response = requests.get(url, timeout=10)
#         response.raise_for_status()  # Check if the request was successful
#
#         # Parse the HTML content with BeautifulSoup
#         soup = BeautifulSoup(response.text, 'html.parser')
#
#         # Remove script and style elements
#         for script_or_style in soup(['script', 'style']):
#             script_or_style.decompose()
#
#         # Extract text
#         text = soup.get_text(separator='\n')
#
#         # Clean up extra whitespace and empty lines
#         cleaned_text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
#
#         return cleaned_text
#
#     except requests.RequestException as e:
#         return f"Error fetching the web page: {e}"
#     except Exception as e:
#         return f"Error parsing the web page: {e}"

async def ddgs_text_search(tool_context: ToolContext) -> dict[str, Any]:
    """
     执行文本搜索，并返回搜索结果。

     该函数会从传入的 `tool_context` 中读取查询参数，使用 aDDGS
     (DuckDuckGo Search 的异步客户端) 在 `cn-zh` 区域执行文本搜索，
     并限制返回结果在过去一年内（`timelimit='y'`），最多 10 条。

     Args:
         tool_context (ToolContext):
             上下文对象，通常包含运行时状态信息。
             - 其中 `tool_context.state["current_parameters"]["query"]`
               用于获取搜索关键词。

     Returns:
         dict[str, Any]: 包含搜索执行状态与结果的字典：
             - "status": str，值为 `"success"` 或 `"error"`。
             - "message":
                 - 当 status 为 `"success"` 时，为搜索结果列表，
                   每个元素为 DuckDuckGo 返回的搜索条目（包含 title、body 等字段）。
                 - 当 status 为 `"error"` 时，为错误信息字符串。

     Example:
         >>> tool_context.state["current_parameters"] = {"task_query": "人工智能"}
         >>> result = await ddgs_text_search(tool_context)
         >>> result["status"]
         'success'
         >>> len(result["message"])
         20

     Notes:
         - 搜索区域固定为中国简体中文（`region='cn-zh'`）。
         - 结果数最多为 10 条。
         - 时间限制为过去一年（`timelimit='y'`）。
         - 若请求过程中发生异常，会返回 `"status": "error"` 和对应的错误描述。
     """
    current_parameters = tool_context.state.get("current_parameters", {})
    query = current_parameters.get("task_query")


    # print('+++++++++++++++ searching ++++++++++++++++++++++')

    try:
        async with aDDGS() as ddgs:
            result = await ddgs.text(
                keywords=query,
                region='cn-zh',
                max_results=10,
                timelimit='y'
            )

            # text = f"找到{len(result)}条相关文本：\n\n"
            # for i, item in enumerate(result):
            #     text += f"【结果{i + 1}】 标题：{item.get('title', '无标题')}，内容：{item.get('body', '无内容')}\n"
            for i, item in enumerate(result):
                url = item.get('href', 'no_url')
                text_content = ''
                if 'no_url' not in url:
                    text_content = get_text_from_url(url)
                    if text_content is not None and len(text_content) > 30 and not text_content.startswith('Error'):
                        result[i]['body'] = text_content
            return {
                "status": "success",
                "message": result
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"duckduckgo-search error: {str(e)}"
        }
