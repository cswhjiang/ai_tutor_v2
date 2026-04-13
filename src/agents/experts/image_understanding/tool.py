from typing import Dict, Any

from dashscope import MultiModalConversation
from google.adk.tools import ToolContext
from google.adk.agents.invocation_context import InvocationContext
from openai import AsyncOpenAI

from conf.api import API_CONFIG
from src.logger import logger
from src.utils import binary_to_base64
from src.agents.experts.image_utils import get_image_info_from_bytes

async def image_to_text_tool(ctx: InvocationContext, input_name: str, mode: str = 'description') -> Dict[str, Any]:
    """
    使用通义千问VL模型分析本地图像并生成相关文本。
    此函数分析单张图片
    """
    tool_name_for_log = "image_to_text_tool"
    
    # 读取artifact，转变成base64格式
    # artifact_part = await tool_context.load_artifact(filename=input_name)
    artifact_part = await ctx.artifact_service.load_artifact(filename=input_name,
                                                             app_name=ctx.session.app_name,
                                                             user_id=ctx.session.user_id,
                                                             session_id=ctx.session.id)
    image_base64 = binary_to_base64(artifact_part.inline_data.data, artifact_part.inline_data.mime_type)

    basic_info = get_image_info_from_bytes(artifact_part.inline_data.data)

    # API-KEY
    DASHSCOPE_API_KEY = API_CONFIG.DASHSCOPE_API_KEY
    if not DASHSCOPE_API_KEY:
        return {
            "status": "error",
            "message": " DASHSCOPE_API_KEY is not set",
        }

    # message
    prompts_map = {
        "description": "请详细描述这张图片的内容，包括主要的物体、场景、氛围以及可能的故事情节。",
        "style": "请分析并描述这张图片的艺术风格，例如绘画流派、色彩运用、构图特点、光影效果以及整体给人的感觉。",
        "ocr": "请提取这张图片中的所有文字内容。如果包含多种语言，请分别列出。",
        "all": "请详细描述这张图片的内容，包括主要的物体、场景、氛围以及可能的故事情节。然后分析并描述这张图片的艺术风格，例如绘画流派、色彩运用、构图特点、光影效果以及整体给人的感觉。最后请提取这张图片中的所有文字内容。如果包含多种语言，请分别列出。",
    }
    text_prompt = prompts_map.get(mode, prompts_map['description'])

    messages = [
        {"role": "system", "content": [{"type":"text", "text": "你是一个专业的图片分析师"}]},
        {"role": "user", "content": 
            [{"type":"text","text": text_prompt}, {"type": "image_url", "image_url":{"url":image_base64}}]
        }
    ]

    # call Qwen-VL
    try:
        logger.info(f"[{tool_name_for_log}] called: name='{input_name}', mode='{mode}'")
        # 换成https://help.aliyun.com/zh/model-studio/vision#c2cd125e14nf7提供的异步访问模式
        async with AsyncOpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ) as client:
            response = await client.chat.completions.create(messages=messages, model='qwen-vl-plus')
        
        logger.info(f"[{tool_name_for_log}] tongyi VL analysis success")
        content = response.choices[0].message.content
        content = content + '这个图像的基本信息为：' + basic_info + '\n'
        return {'status': 'success', 'message': content}

    except Exception as e:
        logger.exception("[{}] 调用通义千问VL失败：{}", tool_name_for_log, e)
        # logger.error(f"[{tool_name_for_log}] calling tongyi VL API have exception: {e}", exc_info=True)
        return {"status": "error", "message": f"calling tongyi VL API have exception: {e}"}
