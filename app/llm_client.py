import base64
import io

import httpx
from PIL import Image


class LLMClient:
    def __init__(self, endpoint: str, api_key: str, model: str, target_language: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.target_language = target_language

    def _encode_image(self, pil_image: Image.Image) -> str:
        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    def translate(self, pil_image: Image.Image) -> str:
        b64 = self._encode_image(pil_image)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "识别图片中的所有英文文字，然后严格按照以下固定格式回复。"
                                "排版、标题顺序、结构绝对不能变，必须包含全部三个段落：\n\n"
                                "【原文】\n"
                                "<完整复制识别出的英文原句，不要做任何修改>\n\n"
                                "【标准中文翻译】\n"
                                "<给出自然、通顺、符合考研英语翻译规范的中文译文>\n\n"
                                "【考研重点词汇解析】\n"
                                "1. 单词 | 音标 | 中文翻译\n"
                                "2. 单词 | 音标 | 中文翻译\n\n"
                                "注意事项：\n"
                                "1. 词汇只列考研大纲核心词，不罗列所有单词；\n"
                                "2. 如果图片中没有英文文字，请在【原文】处写「未识别到文字」，其余段落留空。"
                                "3. 回复中绝对不要写「好的」「明白了」「这是翻译结果」等非格式内容的文字。"
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
        }
        url = self.endpoint.rstrip("/")
        with httpx.Client(timeout=120) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
