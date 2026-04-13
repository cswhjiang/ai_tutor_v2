import asyncio
import os
import os.path
import tempfile
from pathlib import Path
from playwright.async_api import async_playwright
# from src.logger import logger

# 输入 html 字符串 + (name, binary) 列表，输出渲染后的 PNG 二进制
async def html_to_image(html_code: str, img_binary_list):
    with tempfile.TemporaryDirectory() as td:
        html_file_path = os.path.join(td, "index.html")
        with open(html_file_path, "w", encoding="utf-8") as fh:
            fh.write(html_code)

        for img_name, img_bin in img_binary_list:
            safe_name = os.path.basename(img_name)
            with open(os.path.join(td, safe_name), "wb") as fh:
                fh.write(img_bin)

        # logger.info("========== saved to temp dir =======")

        html = Path(html_file_path)
        error_message = ""
        img_message = None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    device_scale_factor=1,
                    viewport={"width": 1024, "height": 768},
                )
                page = await context.new_page()

                # logger.info(f"HTML path: {html}")
                url = html.resolve().as_uri()  # file://...
                await page.goto(url, wait_until="load", timeout=60_000)

                # 如需懒加载支持，可启用下面的滚动
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                out_path = os.path.join(td, "out_html.png")
                await page.screenshot(path=out_path, full_page=True)
                # logger.info("Saved html screenshot to: %s", out_path)

                await context.close()
                await browser.close()

                with open(out_path, "rb") as f:
                    img_message = f.read()
        except Exception as e:
            error_message = str(e)

        if img_message is not None:
            result = {"status": "success", "message": img_message}
        else:
            result = {"status": "error", "message": error_message}

    # logger.info("html_to_image return, status=%s", result["status"])
    return result
