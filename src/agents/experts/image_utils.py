import io
import json
import os
import time
from typing import Optional

import requests
from PIL import Image
from io import BytesIO

from alibabacloud_imageseg20191230.client import Client as ImageSegClient
from alibabacloud_imageseg20191230.models import (
    # SegmentHDCommonImageRequest,
    SegmentHDCommonImageAdvanceRequest,
    GetAsyncJobResultRequest,
)
from alibabacloud_tea_openapi.models import Config
from alibabacloud_tea_util.models import RuntimeOptions

def get_image_info_from_bytes(image_bytes):
    """
    从图像 bytes 中解码图像，并返回图像的宽、高，及是否**实际**包含非不透明像素。
    """
    if not isinstance(image_bytes, (bytes, bytearray)):
        return '图片未成功生成或字节数据无效。'

    try:
        image_stream = io.BytesIO(image_bytes)
        with Image.open(image_stream) as img:
            width, height = img.size
            result = f"Image width: {width}, Image height: {height}\n"

            # 1. 检查 P 模式 (调色板) 透明度
            if img.mode == "P":
                if "transparency" in img.info:
                    # 如果有 transparency 键，则认为**实际具有**透明度
                    result += "**该图片具有透明度 (P 模式带透明信息)。**"
                    return result

            # 2. 检查显式 Alpha 模式 (RGBA, LA, PA) 的实际内容
            if img.mode in ("RGBA", "LA", "PA"):
                # 获取 Alpha 通道
                alpha_channel = img.split()[-1]

                # Alpha 值为 255 表示完全不透明
                # 检查 Alpha 通道中是否有任何像素值小于 255。
                # getbbox() 方法返回包含所有非零像素的最小矩形区域。
                # 对于 Alpha 通道，非零像素即是透明/半透明像素（值 < 255）。

                # 创建一个只包含透明/半透明像素的掩码
                # 1. 转换为 Numpy 数组 (如果需要处理大数据量，更高效)
                #    或者
                # 2. 使用 Image.point() 或 Image.getextrema()

                # **使用 Image.getextrema() 是最简洁且高效的方法**
                # 它返回通道的最小值和最大值
                min_alpha, max_alpha = alpha_channel.getextrema()

                if min_alpha < 255:
                    # 如果最小 Alpha 值小于 255，说明存在透明或半透明像素
                    result += "该图片实际具有透明度 (Alpha 最小值 < 255)。"
                else:
                    # 如果最小 Alpha 值为 255，说明所有像素都是完全不透明的
                    result += "该图片具有 Alpha 通道，但实际内容为完全不透明 (所有 Alpha 值 = 255)。"

                return result

            # 3. 其他模式 (L, RGB, CMYK 等)
            result += "该图片不具有透明度 (无 Alpha 通道)。"
            return result

    except Exception as e:
        return f"获取图像基本信息失败：{e}"

#
# def get_image_info_from_bytes(image_bytes):
#     """
#     从输入的图像 bytes 中解码图像，并返回图像的宽、高，及是否具有透明度。
#     """
#     # 明确检查输入类型
#     if not isinstance(image_bytes, (bytes, bytearray)):
#         return '图片未成功生成或字节数据无效。'
#
#     try:
#         # 读取图像
#         image_stream = io.BytesIO(image_bytes)
#         with Image.open(image_stream) as img:
#             width, height = img.size
#
#             # 基本信息
#             result = f"Image width: {width}, Image height: {height}\n"
#
#             # 判断透明度
#             if img.mode in ("RGBA", "LA", "P"):  # P模式可能带透明信息
#                 # 对 P 模式进一步判断是否存在透明信息
#                 if img.mode == "P" and "transparency" not in img.info:
#                     result += "该图片不具有透明度。"
#                 else:
#                     result += "该图片具有透明度。"
#             else:
#                 result += "该图片不具有透明度。"
#
#             return result
#
#     except Exception as e:
#         return f"获取图像基本信息失败：{e}"


# ===================== 阿里云 Client & 轮询逻辑 =====================

def _create_imageseg_client() -> ImageSegClient:
    """
    创建并返回阿里云图像分割 Client。

    - 从环境变量读取 ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
    - 使用 imageseg.cn-shanghai.aliyuncs.com 作为 endpoint
    """
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    if not access_key_id or not access_key_secret:
        raise RuntimeError("缺少阿里云 AccessKey，请先在环境变量中配置 "
                           "ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    config = Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        endpoint="imageseg.cn-shanghai.aliyuncs.com",
        region_id="cn-shanghai",
    )
    return ImageSegClient(config)


def _poll_async_job_result(
    client: ImageSegClient,
    job_id: str,
    *,
    interval_seconds: float = 2.0,
    max_retries: int = 6,
) -> Optional[bytes]:
    """
    轮询异步任务结果，直到成功 / 失败 / 超时。

    Args:
        client: 已初始化的阿里云 imageseg client。
        job_id: 异步任务的 JobId。
        interval_seconds: 每次轮询间隔（秒）。
        max_retries: 最多轮询次数。

    Returns:
        bytes: 成功时返回下载到的结果图片 bytes。
        None: 失败或超时时返回 None。
    """
    for _ in range(max_retries):
        get_req = GetAsyncJobResultRequest(job_id=job_id)
        get_resp = client.get_async_job_result(get_req)
        result = get_resp.body

        status = result.data.status

        if status == "PROCESS_SUCCESS":
            # result.data.result 是一个 JSON 字符串
            json_obj = json.loads(result.data.result)
            img_url = json_obj.get("imageUrl")
            if not img_url:
                print("未在结果中找到 imageUrl 字段。")
                # return None
                continue

            try:
                resp = requests.get(img_url, timeout=30)
                resp.raise_for_status()
                return resp.content
            except Exception as e:
                print(f"下载结果图片 {img_url} 失败: {e}") ## TODO: bug
                # return None
                continue

        if status in ("FAILED", "FAILURE", "ERROR"):
            print(f"异步任务失败，状态：{status}，详情：{result}")
            # return None
            continue
        time.sleep(interval_seconds)

    print("轮询超时，未在规定次数内获取到成功状态。")
    return None


# ===================== 对外主函数 =====================

def make_background_transparent_bytes(image_bytes: bytes) -> bytes:
    """
    使用阿里云图像分割服务，将图片背景变为透明并返回新的 PNG 字节数据。

    注意：
        当前实现完全依赖阿里云 imageseg 接口进行背景分割，
        threshold 参数暂未参与计算，保留只是为了兼容原有接口签名。

    Args:
        image_bytes: 原始图片的二进制数据。

    Returns:
        新 PNG 图片的字节数据。如果失败则返回 b""。
    """

    try:
        client = _create_imageseg_client()

        # 构造高清通用图像分割请求
        # segment_req = SegmentHDCommonImageRequest()
        segment_req = SegmentHDCommonImageAdvanceRequest()

        # 使用 BytesIO 包装二进制数据
        segment_req.image_url_object = BytesIO(image_bytes)

        runtime = RuntimeOptions(
            read_timeout=30000,    # 30 秒
            connect_timeout=10000  # 10 秒
        )

        # 提交异步任务
        submit_resp = client.segment_hdcommon_image_advance(segment_req, runtime)
        submit_body = submit_resp.body
        # 这里沿用你原来的逻辑：job_id 使用 RequestId
        job_id = submit_body.request_id

        if not job_id:
            print("提交任务失败：未获取到 job_id。")
            return b""

        # 轮询获取结果
        result_bytes = _poll_async_job_result(client, job_id)
        if result_bytes is None:
            return b""

        return result_bytes

    except Exception as error:
        # 打印详细错误信息，但不要抛出到外层，保证函数返回类型稳定
        print("调用阿里云图像分割接口时发生错误：", error)
        # 如果 SDK 的错误对象具有 code 属性，可打印出来
        if hasattr(error, "code"):
            print("Error code:", getattr(error, "code"))
        return b""

def _ratio_to_float(r):
    a, b = map(float, r.split(':'))
    return a / b

def select_aspect_ratio(as_in:str, as_list=['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9']):
    if as_in is None or (not isinstance(as_in, str)) :
        return '1:1'

    if ':' not in as_in:
        return '1:1'

    as_in_value = _ratio_to_float(as_in)
    min_index = 0
    d = 99999
    for i, a in enumerate(as_list):
        v = _ratio_to_float(a)
        if abs(v - as_in_value) < d:
            min_index = i
            d = abs(v - as_in_value)

    return as_list[min_index]