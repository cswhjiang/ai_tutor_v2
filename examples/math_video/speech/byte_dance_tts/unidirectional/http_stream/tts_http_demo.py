# -*- coding: utf-8 -*-
# @Project : tob_service
# @Company : ByteDance
# @Time    : 2025/7/10 19:01
# @Author  : SiNian
# @FileName: TTSv3HttpDemo.py
# @IDE: PyCharm
# @Motto：  I,with no mountain to rely on,am the mountain myself.
import requests
import json
import base64
import os

# python版本：==3.11
# latex 能力说明 https://bytedance.larkoffice.com/docx/ZjFidvxSZov7TYxuUbzctpPonqe
# latex标签的内容用 \( 或者 $ 包含

def tts_http_stream(url, headers, params, audio_save_path):
    session = requests.Session()
    try:
        print('请求的url:', url)
        print('请求的headers:', headers)
        print('请求的params:\n', params)
        response = session.post(url, headers=headers, json=params, stream=True)
        print(response)
        # 打印response headers
        print(f"code: {response.status_code} header: {response.headers}")
        logid = response.headers.get('X-Tt-Logid')
        print(f"X-Tt-Logid: {logid}")

        # 用于存储音频数据
        audio_data = bytearray()
        total_audio_size = 0
        for chunk in response.iter_lines(decode_unicode=True):
            if not chunk:
                continue
            data = json.loads(chunk)

            if data.get("code", 0) == 0 and "data" in data and data["data"]:
                chunk_audio = base64.b64decode(data["data"])
                audio_size = len(chunk_audio)
                total_audio_size += audio_size
                audio_data.extend(chunk_audio)
                continue
            if data.get("code", 0) == 0 and "sentence" in data and data["sentence"]:
                print("sentence_data:", data)
                continue
            if data.get("code", 0) == 20000000:
                if 'usage' in data:
                    print("usage:", data['usage'])
                break
            if data.get("code", 0) > 0:
                print(f"error response:{data}")
                break

        # 保存音频文件
        if audio_data:
            with open(audio_save_path, "wb") as f:
                f.write(audio_data)
            print(f"文件保存在{audio_save_path},文件大小: {len(audio_data) / 1024:.2f} KB")
            # 确保生成的音频有正确的访问权限
            os.chmod(audio_save_path, 0o644)

    except Exception as e:
        print(f"请求失败: {e}")
    finally:
        response.close()
        session.close()

def text_to_mp3(ssml):
    # -------------客户需要填写的参数----------------
    appID = os.getenv("VOLCENGINE_APPID")
    accessKey = os.getenv("VOLCENGINE_ACCESS_TOKEN")

    resourceID = "seed-tts-1.0"
    speaker = "zh_female_yingyujiaoyu_mars_bigtts"
    # text = "乘法交换律：$a \times b = b \times a$，乘法交换律：\(a \times b = b \times a\)。"
    # text = "乘法交换律：\(a \times b = b \times a\)" # 数学分隔符之后需要加标点，更加鲁棒。

    # resourceID = "seed-tts-2.0"
    # text = "这是一段测试文本，用于测试字节大模型语音合成http单向流式接口效果。"
    # speaker = "zh_female_xiaohe_uranus_bigtts"
    # ssml = """<speak>
    #   欢迎关注<sub alias="万维网">WWW</sub>联盟，
    #   <break time="300ms"/>我们将为您提供最新<sub alias="人工智能">AI</sub>资讯。
    # </speak>"""

    # ---------------请求地址----------------------
    url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"

    # ---------------请求地址----------------------
    headers = {
        "X-Api-App-Id": appID,
        "X-Api-Access-Key": accessKey,
        "X-Api-Resource-Id": resourceID,
        "Content-Type": "application/json",
        "Connection": "keep-alive",

        # 表示是否需要用量返回, 默认不添加; 启用后在合成结束时会多一个usage字段
        # "X-Control-Require-Usage-Tokens-Return": "*"
    }

    payload = {
        "user": {
            "uid": "123123"
        },
        "req_params": {
            # "text": text,
            "ssml": ssml,
            "speaker": speaker,
            "audio_params": {
                "format": "mp3",
                "sample_rate": 24000,
                "enable_timestamp": True
            },
            # "additions": "{\"explicit_language\":\"zh-cn\", \"latex_parser\":\"\",\"disable_markdown_filter\":true, \"enable_timestamp\":true}\"}",
            "additions": "{\"explicit_language\":\"zh-cn\", \"latex_parser\":\"v2\",\"disable_markdown_filter\":true, \"enable_timestamp\":true}\"}",
            # "additions": "{\"explicit_language\":\"zh-cn\", \"enable_latex_tn\":false,\"disable_markdown_filter\":true, \"enable_timestamp\":true}\"}"
        }
    }

    tts_http_stream(url=url, headers=headers, params=payload, audio_save_path=f"tts_test_{speaker}.mp3")

if __name__ == "__main__":
    ssml = """<speak>
            Welcome to our advanced mathematics session. 
            <break time="1s"/>
            Today, we will focus on the relationship between variables.
          <break time="1s"/>
          已知函数 $f(x)$ 的定义域是全体实数，
          <break time="1s"/>
          且满足方程  $\delta = 0.618$。
          乘法交换律：$a \times b = b \times a$，
    乘法交换律：\(a \times b = b \times a\)。
        </speak>"""  # ssml 只使用 break、speak
    ssml = """<speak>
            Welcome to our advanced mathematics session. 
            <break time="1s"/>
            Today, we will focus on the relationship between variables.
          <break time="1s"/>
          已知函数 $f(x)$ 的定义域是全体实数，且满足方程  $\\delta = 0.618$。乘法交换律：$a \\times b = b \\times a$，乘法交换律：\\(a \\times b = b \\times a\\)。
        </speak>"""  # ssml 只使用 break、speak，公式只用 $$，speak 标签最好用空格或者换行分隔开。
    ssml = r"""<speak> Welcome to our advanced mathematics session. <break time="1s"/> 已知函数 $f(x)$ 的定义域是全体实数，<break time="500ms"/> 且满足方程 $\\delta = 0.618$。 </speak>"""
    # ssml = """<speak>测试<break time=\"1s\"/>停顿</speak>"""
    print(ssml)
    text_to_mp3(ssml)



