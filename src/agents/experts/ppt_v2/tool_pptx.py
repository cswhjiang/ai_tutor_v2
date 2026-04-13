import asyncio
import os
import os.path
import tempfile
from pathlib import Path
from src.logger import logger
import subprocess
import sys
from pathlib import Path
import shutil

async def run_create_ppt(workdir, js_path):
    env_result_1 = subprocess.run(["npm", "init", "-y"],  capture_output=True,cwd=workdir, text=True)
    env_result_2 = subprocess.run(["npm", "install", "pptxgenjs", "playwright", "sharp"], capture_output=True, cwd=workdir, text=True)
    env_result_3 = subprocess.run(["npx", "playwright", "install", "chromium"], capture_output=True, cwd=workdir, text=True)
    result = subprocess.run(
        ["node", js_path],
        capture_output=True,
        cwd=workdir,
        text=True
    )

    return {
        "ok": result.returncode == 0 and env_result_1.returncode == 0 and env_result_2.returncode == 0 and env_result_3.returncode == 0,
        "stdout": env_result_1.stdout + '\n' + env_result_2.stdout + '\n' + env_result_3.stdout + '\n' + result.stdout,
        "stderr": env_result_1.stderr + '\n' + env_result_2.stderr + '\n' + env_result_3.stderr + '\n' + result.stderr,
        "code": str(result.returncode)
    }


async def html_to_pptx(html_codee_all_pages: str, html_single_pages: dict, img_binary_list, create_js: str, suggested_width=1024, suggested_height=768):

    with tempfile.TemporaryDirectory(delete=False) as td:
        logger.info(td)
        for k, v in html_single_pages.items():
            html_file_path = os.path.join(td, f"{k}.html")
            with open(html_file_path, "w", encoding="utf-8") as fh:
                fh.write(v)

        for img_name, img_bin in img_binary_list:
            # safe_name = os.path.basename(img_name)
            save_name = os.path.join(td, img_name)
            folder_path = os.path.dirname(save_name)
            os.makedirs(folder_path, exist_ok=True)
            with open(save_name, "wb") as fh:
                fh.write(img_bin)

        html_all_save_path = os.path.join(td,  'index.html')
        with open(html_all_save_path, "w", encoding="utf-8") as fh:
            fh.write(html_codee_all_pages)

        create_js_path = os.path.join(td, "create_ppt.js")
        with open(create_js_path, "w", encoding="utf-8") as fh:
            fh.write(create_js)

        cwd = os.getcwd()
        src_file = os.path.join(cwd, "src/agents/experts/ppt_v2/html2pptx.js")
        shutil.copy(src_file, td)

        result = await run_create_ppt(td, create_js_path)
        logger.info(result)
        pptx_bin = None
        if not result['ok']:
            error_message = result['stdout'] + '\n' + result['stderr'] + '\n' + result['code']
        else:
            pptx_files = []

            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(".pptx"):
                        full_path = os.path.abspath(os.path.join(root, file))
                        pptx_files.append(full_path)

            # pptx_files 的长度应该是1
            if len(pptx_files) > 0:
                pptx_result = pptx_files[0]
                with open(pptx_result, 'rb') as f:
                    pptx_bin = f.read()
            else:
                error_message = "pptx 文件生成失败"



        if pptx_bin is not None:
            result = {"status": "success", "message": pptx_bin}
        else:
            result = {"status": "error", "message": error_message}

        return result