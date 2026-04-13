import asyncio
import os.path
import tempfile
from pathlib import Path
from playwright.async_api import async_playwright

# from src.logger import logger

# html = Path(r"/Users/wenhaojiang/Downloads/pdp.html")
# OUT_DIR = Path(r"./shots")
# OUT_DIR.mkdir(exist_ok=True)

# 输入html代码和需要的图像的二进制，输出渲染之后图像的二进制
async def html_to_image(html_code, img_binary_list):
    # img_binary_list 是 (name, img_binary) 类型的列表
    with tempfile.TemporaryDirectory() as td:
        html_file_path = os.path.join(td, 'index.html')
        with open(html_file_path, 'w', encoding='utf-8') as fh:
            fh.write(html_code)

        for img_file in img_binary_list:
            img_name = img_file[0]
            img_bin = img_file[1]
            img_file_path = os.path.join(td, img_name)
            with open(img_file_path, 'wb') as fh:
                fh.write(img_bin)

        # logger.info('========== saved to temp dir =======')
        html = Path(html_file_path)
        error_message = ''
        img_message = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(device_scale_factor=2)  # 高清
                page = await context.new_page()

                # logger.info(html)
                url = html.resolve().as_uri()  # file://...
                await page.goto(url, wait_until="networkidle", timeout=60_000)

                # 如果页面高度依赖窗口宽度，可设置 viewport
                await page.set_viewport_size({"width": 72, "height": 72})
                out_path = os.path.join(td, "out_html.png")
                await page.screenshot(path=str(out_path), full_page=True)
                # logger.info(f"Saved html screenshot to: {out_path}")

                await browser.close()
                with open(out_path, 'rb') as f:
                    img_message = f.read()
        except Exception as e:
            error_message = str(e)

        if img_message is not None:
            result = {'status': "success", "message": img_message}
        else:
            result = {'status': "error", "message": error_message}

    # logger.info('html_to_image return')
    # logger.info(result)
    return result

# async def main():
#     with open(html, 'r', encoding="utf-8") as f:
#         html_code = f.read()
#     result = await html_to_image(html_code, [])
#     print(result)
#
# if __name__ == "__main__":
#     asyncio.run(main())