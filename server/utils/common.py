import os
import json
import time
import zipfile
import tempfile
import argparse
import asyncio
import requests
import httpx
from pathlib import Path
from typing import Optional, List, Union
import pypandoc


from pdfdeal import Doc2X

from src.logger import logger
from conf.system import SYS_CONFIG
from google.genai.types import Content, Part
from google.adk.events import Event, EventActions
from server.utils.util import load_file_as_part
from server.agents_manager import session_service, artifact_service
from src.utils import database_op_with_retry


from pdfdeal.Doc2X.ConvertV2 import (
    upload_pdf,
    uid_status,
    convert_parse,
    get_convert_result,
)

def _is_retryable_convert_parse_error(e: Exception) -> bool:
    """
    判断是否是 Doc2X 在 UID 未就绪阶段常见的“伪参数错误”
    """
    s = str(e)
    return (
        "Conversion request failed" in s
        and ":400:" in s
        and "bad_request" in s
    )

async def convert_parse_outer_retry(
    *,
    apikey: str,
    uid: str,
    to_format: str,
    max_rounds: int = 5,
    base_sleep_s: float = 2.5,
    max_sleep_s: float = 12.0,
):
    """
    外层重试：
    - 每一轮调用 convert_parse（它自己会重试 3 次，每次 1 秒）
    - 若失败，等待更长时间再重来
    """
    sleep_s = base_sleep_s
    last_err = None

    for round_idx in range(1, max_rounds + 1):
        try:
            return await convert_parse(
                apikey=apikey,
                uid=uid,
                to=to_format,
            )
        except Exception as e:
            last_err = e

            # 非“UID 未就绪型错误” -> 立即抛出
            if not _is_retryable_convert_parse_error(e):
                raise

            if round_idx >= max_rounds:
                break

            # 👉 关键点：给服务端“足够时间”
            await asyncio.sleep(sleep_s)
            sleep_s = min(sleep_s * 1.8, max_sleep_s)

    raise TimeoutError(
        f"convert_parse 在外层重试 {max_rounds} 轮后仍失败，"
        f"很可能 Doc2X 后端处理异常或 UID 永久不可用。"
    ) from last_err


async def pdf_2_md(pdf_path: str, to_format: str='md_dollar', max_wait: int=10, interval: int=3):
    api_key = os.getenv("DOC2X_API_KEY")
    if not api_key:
        raise RuntimeError("环境变量 DOC2X_API_KEY 未设置。请先 export DOC2X_API_KEY=你的key")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"找不到 PDF 文件: {pdf_path}")

    # 1) 上传文件，获得 UID（后台开始转换）
    uid = await upload_pdf(apikey=api_key, pdffile=pdf_path)
    print("UID:", uid)
    # time.sleep(3)

    # 2) 查询上传/处理状态
    # process, status, texts, locations = await uid_status(apikey=api_key, uid=uid)
    # print("UID Status:", process, status, texts, locations)
    await asyncio.sleep(3)
    # await asyncio.sleep(10) # sleeep 时间过短 convert_parse 会出现错误

    # 3) 发起转换请求
    # convert_parse 执行前不sleep 容易出错
    # status, url = await convert_parse(apikey=api_key, uid=uid, to=to_format)
    # print("Convert Parse:", status, url)

    status, url = await convert_parse_outer_retry(
        apikey=api_key,
        uid=uid,
        to_format=to_format,
        max_rounds=5,  # 等价于“最多等 ~30~40 秒”
        base_sleep_s=2.5,  # 第一轮失败后等 2.5s
    )
    print("Convert Parse:", status, url)

    # 4) 轮询获取结果
    for i in range(1, max_wait + 1):
        status, url = await get_convert_result(apikey=api_key, uid=uid)
        print(f"[{i}/{max_wait}] Result:", status, url)

        if isinstance(status, str) and status.lower() == "success":
            print("✅ 转换成功！结果 URL:", url)

            # pdf_path = os.path.abspath(pdf_path)
            pdf_name, file_ext = os.path.splitext(os.path.basename(pdf_path))
            timeout: int = 30
            with tempfile.TemporaryDirectory(delete=False) as td: #
                out_dir = os.path.join(td, pdf_name)
                out_dir = os.path.abspath(out_dir)
                os.makedirs(out_dir, exist_ok=True)

                zip_path = os.path.join(out_dir, pdf_name + ".zip")
                with requests.get(url, stream=True, timeout=timeout) as r:
                    r.raise_for_status()
                    with open(zip_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
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

                md_path = os.path.join(out_dir, new_md_file)
                md_path = os.path.abspath(md_path)

                image_path = os.path.join(out_dir, 'images')
                print(out_dir, md_path, image_path)
                return out_dir, md_path, image_path  # 都是绝对路径

        await asyncio.sleep(interval)

    print("❌ 超时：在设定的等待次数内未获得 success。最后一次状态:", status, url)
    return None


def ensure_pandoc():
    try:
        # 检查pandoc是否可用
        pypandoc.get_pandoc_version()
    except OSError:
        # 如果不可用，则下载
        pypandoc.download_pandoc()


async def docx_to_md_with_images_pandoc(
    input_docx_path: str,
    fmt: str = "gfm",  # 也可以用 "markdown" / "markdown_strict"
):
    ensure_pandoc()

    doc_name, doc_ext = os.path.splitext(os.path.basename(input_docx_path))

    with tempfile.TemporaryDirectory(delete=False) as td:
        out_dir = os.path.join(td, doc_name)
        os.makedirs(out_dir, exist_ok=True)

        out_md_path = os.path.join(out_dir, f"{doc_name}.md")
        # media_dir = os.path.join(out_dir, 'images')
        media_dir = out_dir

        extra_args = [
            f"--extract-media={media_dir}",
        ]
        prefix_to_replace = out_dir

        pypandoc.convert_file(
            source_file=str(input_docx_path),
            to=fmt,
            format="docx",
            outputfile=str(out_md_path),
            extra_args=extra_args,
        )

        with open(out_md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        content = content.replace(out_dir, '.')

        with open(out_md_path, 'w', encoding='utf-8') as f:
            f.write(content)

        media_dir = os.path.join(media_dir, 'media') # pypandoc 默认增加了一级 media 文件夹
        os.makedirs(media_dir, exist_ok=True)
        return str(out_md_path), str(media_dir) # 绝对路径


# --- state定义以及初始化 ---
async def set_initial_state(uid:str, sid:str, message:str, img_paths: Optional[List[Union[str, None]]] = None, doc_paths: Optional[List[Union[str, None]]] = None) -> None:
    """
    此函数用户初始化当前session的state，会在每次接收到用户指令后执行
    state中的*history部分会保留当前session之前的历史信息(即之前的多轮对话)
    """
    init_key = [
        'app_name',
        'uid',
        'sid',
        'user_prompt',          # 当前用户任务
        'global_plan',          # 当前任务的总体规划
        'current_plan',         # 当前的步骤规划
        'step',                 # 已执行的步数（多轮对话会累加而不是归零）
        'input_artifacts',      # 当前任务输入图片
        'artifacts_history',    # 执行输出artifact历史
        'text_history'          # 执行输出的文本历史
        'new_artifacts',        # 当前步骤新输出的artifact或一开始的artifact
        'summary_history',      # 执行输出summary历史
        'temp_parameter',        # 临时参数存储，用于灵活调用场景，会在每次执行后清除
        'search_count',          # search 工具调用了多少次。希望在一个session里面不要调用太多次，防止一直搜索总结不结束
        
    ]
    logger.info(f"init state: uid: {uid}, sid: {sid}")
    logger.info(img_paths)
    logger.info(doc_paths)
    current_session = await database_op_with_retry(
                session_service.get_session,
                app_name=SYS_CONFIG.app_name,
                user_id=uid,
                session_id=sid,
            )

    state_delta = {}
    # for k in current_session.state.keys(): # bug, 如果state中之前已经存在的key，不需要清空
    #     state_delta[k] = None

    state_delta['app_name'] = SYS_CONFIG.app_name
    state_delta['uid'] = uid
    state_delta['sid'] = sid
    state_delta['user_prompt'] = message
    state_delta['global_plan'] = None
    state_delta['current_plan'] = None

    if 'step' in current_session.state:
        state_delta['step'] = current_session.state['step']
    else:
        state_delta['step'] = 0

    if 'search_count' in current_session.state:
        state_delta['search_count'] = current_session.state['search_count']
    else:
        state_delta['search_count'] = 0
    
    state_delta['input_artifacts'] = []
    if img_paths:
        for index, img_path in enumerate(img_paths, start=1):
            if img_path:
                image_name = os.path.basename(img_path)
                state_delta['input_artifacts'].append({
                    'name': image_name, 
                    'path': img_path, 
                    'description': f"The {index}-th raw image input by the user"
                })
                state_delta['user_prompt'] += f"\nThe name of the {index}-th input image is {image_name}"

                await artifact_service.save_artifact(
                    app_name=SYS_CONFIG.app_name,
                    user_id=uid,
                    session_id=sid,
                    filename=image_name,
                    artifact=load_file_as_part(img_path)
                )
                logger.info(f"Input image {index} has been loaded into the artifact service, name: {image_name}")

    if doc_paths:
        logger.info(doc_paths)
        for index, doc_path in enumerate(doc_paths, start=1):
            if doc_path:
                doc_name = os.path.basename(doc_path)
                state_delta['input_artifacts'].append({
                    'name': doc_name,
                    'path': doc_path,
                    'description': f"The {index}-th document input by the user"
                })
                state_delta['user_prompt'] += f"\nThe name of the {index}-th input document is {doc_name}"

                await artifact_service.save_artifact(
                    app_name=SYS_CONFIG.app_name,
                    user_id=uid,
                    session_id=sid,
                    filename=doc_name,
                    artifact=load_file_as_part(doc_path)
                )
                logger.info(f"Input document {index} has been loaded into the artifact service, name: {doc_name}")

                file_name, file_ext = os.path.splitext(os.path.basename(doc_path))
                # NOTE: 统一形式 input_file/input_file.md, 图像放在 input_file/images/image1.png

                # 以下是需要转成md格式，提取文本和图像。
                md_path = None
                md_image_path = None
                if file_ext == '.pdf':
                    _, md_path, md_image_path = await pdf_2_md(doc_path) # md_path 是md文件的路径， md_image_path 是图像路径, xx/images/
                elif file_ext == '.docx':
                    md_path, md_image_path = await docx_to_md_with_images_pandoc(doc_path) # md中的图像路径 是 xxx/media/
                else:
                    pass # TODO: 增加其他类型支持

                if md_path:
                    md_name = os.path.basename(md_path)
                    artifact_md_name = file_name + '/' + md_name
                    state_delta['input_artifacts'].append({
                        'name': artifact_md_name,
                        'path': md_path,
                        'description': f"{doc_name}对应的md文件"
                    })
                    state_delta['user_prompt'] += f"\n{doc_name}对应的md文件是 {artifact_md_name}"

                    await artifact_service.save_artifact(
                        app_name=SYS_CONFIG.app_name,
                        user_id=uid,
                        session_id=sid,
                        filename=artifact_md_name,
                        artifact=load_file_as_part(md_path)
                    )
                    logger.info(f"{doc_name}已经完成转换，对应的md文件是{artifact_md_name} ，已经加载进artifact。")

                    for i, img_path in enumerate(os.listdir(md_image_path), start=1):
                        if file_ext == '.pdf':
                            artifact_image_name = file_name + '/images/' + img_path
                        elif file_ext == '.docx':
                            artifact_image_name = file_name + '/media/' + img_path
                        else:
                            artifact_image_name = file_name + '/images/' + img_path

                        img_path = os.path.join(md_image_path, img_path)
                        state_delta['input_artifacts'].append({
                            'name': artifact_image_name,
                            'path': img_path,
                            'description': f"{doc_name}对应的md文件中的第{i}个图像"
                        })
                        state_delta['user_prompt'] += f"\n{doc_name}对应的md文件 {artifact_md_name}中的图像 {i} {artifact_image_name}。"

                        await artifact_service.save_artifact(
                            app_name=SYS_CONFIG.app_name,
                            user_id=uid,
                            session_id=sid,
                            filename=artifact_image_name,
                            artifact=load_file_as_part(img_path)
                        )
                        logger.info(f"{doc_name}已经完成转换，对应的md文件是{artifact_md_name}，对应的图像 {artifact_image_name} 已经加载进artifact。")




    state_delta['artifacts_history'] = [] if not 'artifacts_history' in current_session.state else current_session.state['artifacts_history']
    state_delta['summary_history'] = [] if not 'summary_history' in current_session.state else current_session.state['summary_history']
    state_delta['text_history'] = [] if not 'text_history' in current_session.state else current_session.state['text_history']
    state_delta['message_history'] = [] if not 'message_history' in current_session.state else current_session.state['message_history']
    
    state_delta['new_artifacts'] = state_delta['input_artifacts']

    event = Event(
        author='api_server',
        # content=Content(role='user', parts=[Part(text=f"用户输入新的任务：{state_delta['user_prompt']}，可以开始进行分析")]),
        content=Content(role='user', parts=[Part(text=f"The user has input a new task: {state_delta['user_prompt']}, analysis can begin")]),
        actions=EventActions(state_delta=state_delta)
    )
    # await session_service.append_event(current_session, event)
    # 使用带重试的写入，防止数据库锁定失败
    await database_op_with_retry(
        session_service.append_event,
        session=current_session,
        event=event,
        logger=logger,
        op_name="set_initial_state_append_event"
    )