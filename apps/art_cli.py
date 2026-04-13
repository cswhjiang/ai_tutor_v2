# art_cli.py
import asyncio
import httpx  # *** 替换 aiohttp 为 httpx ***
import argparse
import os
import json
import re
from typing import Optional, Tuple, List
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conf.system import SYS_CONFIG

API_BASE_URL = f"http://localhost:{SYS_CONFIG.api_port}"
# httpx 使用不同的超时配置对象
CLIENT_TIMEOUT = httpx.Timeout(30.0, connect=5.0, read=900.0, write=5.0)


# def parse_message_for_paths_cli(
#         message: str,
# ) -> Tuple[str, Optional[str], Optional[str]]:
#     """(客户端版本) 从用户消息中解析出核心指令和图片路径。"""
#     img1_path = None
#     img2_path = None
#     img3_path = None
#     img4_path = None
#     img5_path = None
#
#     img1_match = re.search(r'图片1:\s*([\'"]?)(.*?)\1(?=\s+图片2:|$)', message, re.IGNORECASE)
#     if img1_match:
#         img1_path = img1_match.group(2).strip()
#
#     img2_match = re.search(r'图片2:\s*([\'"]?)(.*?)\1(?=\s+图片3:|$)', message, re.IGNORECASE)
#     if img2_match:
#         img2_path = img2_match.group(2).strip()
#
#     img3_match = re.search(r'图片3:\s*([\'"]?)(.*?)\1(?=\s+图片4:|$)', message, re.IGNORECASE)
#     if img3_match:
#         img3_path = img3_match.group(2).strip()
#
#     img4_match = re.search(r'图片4:\s*([\'"]?)(.*?)\1(?=\s+图片5:|$)', message, re.IGNORECASE)
#     if img4_match:
#         img4_path = img4_match.group(2).strip()
#
#     img5_match = re.search(r'图片5:\s*([\'"]?)(.*?)\1(?=\s+图片1:|$)', message, re.IGNORECASE)
#     if img5_match:
#         img5_path = img5_match.group(2).strip()
#
#
#     core_prompt = re.sub(
#         r'图片\d:\s*([\'"]?)(.*?)\1', "", message, flags=re.IGNORECASE
#     ).strip()
#     return core_prompt, img1_path, img2_path, img3_path, img4_path, img5_path


async def create_session(
        client: httpx.AsyncClient, user_id: Optional[str]
) -> Optional[str]:
    """使用 httpx 创建会话。"""
    if not user_id:
        user_id = "+cli_user_0000+"
    payload = {"user_id": user_id, "username": 'cli_user'}
    try:
        response = await client.post(
            f"{API_BASE_URL}/session/create", data=payload, timeout=30.0
        )
        response.raise_for_status()  # 检查 HTTP 错误
        data = response.json()
        print(f"Session created successfully: ID = {data['session_id']}, User = {data['user_id']}")
        return data['user_id'], data["session_id"]
    except httpx.RequestError as e:
        print(f"Error creating session request: {e}. Please ensure that the API server has been started at {API_BASE_URL}.")
        return None
    except Exception as e:
        print(f"An unknown error occurred while creating the session: {e}")
        return None


async def send_chat_message(
        client: httpx.AsyncClient,
        core_prompt: str,
        session_id: str,
        user_id: Optional[str],
        img_paths: Optional[List[str]] = None,
        doc_paths: Optional[List[str]] = None,
):
    """使用 httpx 发送包含文件的流式请求。"""
    # core_prompt, img1_path, img2_path = parse_message_for_paths_cli(
    #     full_message_with_paths
    # )

    # httpx 使用 'data' 存放表单字段，'files' 存放文件
    payload_data = {
        "message": core_prompt,
        "session_id": session_id,
        "user_id": user_id or "",
    }

    files_to_upload = []

    # 图片（注意 key 必须都叫 images）
    for img_path in img_paths or []:
        if img_path and os.path.exists(img_path):
            files_to_upload.append(
                (
                    "images",
                    (
                        os.path.basename(img_path),
                        open(img_path, "rb"),
                    ),
                )
            )

    # 文档（key 必须叫 documents）
    for doc_path in doc_paths or []:
        if doc_path and os.path.exists(doc_path):
            files_to_upload.append(
                (
                    "documents",
                    (
                        os.path.basename(doc_path),
                        open(doc_path, "rb")
                    ),
                )
            )

    print(f"\nCLI: Instruction sent to Agent: '{core_prompt}' (Session: {session_id}, User: {user_id or 'Default'})")

    try:
        async with client.stream(
                "POST",
                f"{API_BASE_URL}/chat",
                data=payload_data,
                files=files_to_upload,
                timeout=CLIENT_TIMEOUT,
        ) as response:
            response.raise_for_status()
            print("\n--- Agent Execution Flow ---")
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    try:
                        json_data_str = line[len("data:"):].strip()
                        if not json_data_str:
                            continue
                        event_data = json.loads(json_data_str)
                        event_type = event_data.get("type")
                        event_content = event_data.get("content")

                        if event_type == "step":
                            print(f"  - {event_content}")
                        elif event_type == "final":
                            print("\n--- Agent Final Response ---")
                            print(f" Summary: {event_content.get('text')}")
                            if event_content.get("final_output_text"):
                                print(
                                    f" Detailed Output: {event_content['final_output_text']}"
                                )

                            if event_content.get("image"):
                                image_base64 = event_content["image"]
                                print(f"{len(image_base64)} images have been returned") # TODO: 为什么返回的视频会执行到这里。
                            
                            filenames = event_content.get("filenames")
                            if filenames:
                                print("Generated filenames:")
                                for fname in filenames:
                                    print(f" - {fname}")

                        elif event_type == "error":
                            print(f"\n--- Backend Error ---")
                            print(f" Error Message: {event_content}")
                    except json.JSONDecodeError:
                        print(f"[CLI Warning] Failed to parse SSE event: {line}")
                    except Exception as e:
                        print(f"[CLI Error] Error occurred while processing event: {e}")

    except httpx.RequestError as exc:
        print(f"A client error occurred while sending a message to the API: {exc}")
    except Exception as e:
        print(f"An unknown error occurred while processing the chat: {e}")
        import traceback

        traceback.print_exc()
    finally:
        pass


async def main():
    parser = argparse.ArgumentParser(description="Art Creation Multi-Agent System CLI.")
    parser.add_argument("--user-id", type=str, help="User ID for the session. Overrides the default value.")
    parser.add_argument("--session-id", type=str, help="Continue an existing session ID.")
    parser.add_argument("--message", type=str, help="Send a single message and exit (non-interactive mode).")
    parser.add_argument("--imgs", type=str, default=None, help="Path to image in non-interactive mode. separate multiple paths with commas.")
    parser.add_argument("--docs", type=str, default=None, help="Path to document in non-interactive mode. separate multiple paths with commas.")
    args = parser.parse_args()
    # p = '/data/zhaoyuhang/develop/auto_creative_agent_v4/unit_test/figs'
    # imgs = [os.path.join(p, f) for f in os.listdir(p) if f.endswith((".png", ".jpg", ".jpeg"))]

    # p = '/data/zhaoyuhang/develop/auto_creative_agent_v4/unit_test/files'
    # docs = [os.path.join(p, f) for f in os.listdir(p)]
    imgs = args.imgs.split(",") if args.imgs else None
    docs = args.docs.split(",") if args.docs else None

    async with httpx.AsyncClient() as client:
        current_session_id = args.session_id
        if not current_session_id:
            print("No session ID provided, creating a new one...")
            final_user_id_for_chat, current_session_id = await create_session(client, args.user_id)
            if not current_session_id:
                print("Unable to establish a session. Exiting...")
                return
        else:
            print(f"Attempting to use existing session ID: {current_session_id}")
            final_user_id_for_chat = args.user_id or ""
        # final_user_id_for_chat = args.user_id or SYS_CONFIG.user_id_default
        print(
            f"\nIn conversation with the Art Director AI (User: {final_user_id_for_chat}, Session: {current_session_id})."
        )

        if args.message:
            message = args.message
            await send_chat_message(
                client, message, current_session_id, final_user_id_for_chat, img_paths=imgs,
                doc_paths=docs
            )
            return

        print("Type 'exit' to end the conversation.")
        while True:
            try:
                user_message_base = input("\nYou (enter instruction): ").strip()
                if user_message_base.lower() == "exit":
                    print("Exiting the conversation...")
                    break
                if not user_message_base:
                    continue

                full_message = user_message_base
                docs = []
                while True:
                    doc_path_text = input("Document path (optional, press Enter to skip): ").strip()
                    if doc_path_text.strip():
                        if os.path.exists(doc_path_text):
                            docs.append(doc_path_text)
                        else:
                            print(f"File does not exist: {doc_path_text}. Please re-enter.")
                    else:
                        break
                
                img_paths = []
                while True:
                    img_path_text = input("Image path (optional, press Enter to skip): ").strip()
                    if img_path_text.strip():
                        if os.path.exists(img_path_text):
                            img_paths.append(img_path_text)
                        else:
                            print(f"File does not exist: {img_path_text}. Please re-enter.")
                    else:
                        break

                await send_chat_message(
                    client, full_message, current_session_id, final_user_id_for_chat, img_paths=img_paths, doc_paths=docs
                )

            except KeyboardInterrupt:
                print("\nExiting the conversation...")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                import traceback

                traceback.print_exc()


if __name__ == "__main__":
    print(f"CLI started, application name '{SYS_CONFIG.app_name}', API address {API_BASE_URL}")
    asyncio.run(main())
