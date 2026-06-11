"""
OCR 客户端封装（预留）

TODO: 接入 OCR 服务用于识别图片中的题目文本
"""

# import httpx
# from typing import Optional

# class OCRClient:
#     """光学字符识别客户端"""
#
#     def __init__(self, base_url: str = "http://localhost:5000"):
#         self.base_url = base_url
#         self.client = httpx.AsyncClient(timeout=30)
#
#     async def recognize(self, image_bytes: bytes) -> str:
#         """识别图片中的文字"""
#         resp = await self.client.post(
#             f"{self.base_url}/ocr",
#             files={"image": image_bytes},
#         )
#         resp.raise_for_status()
#         return resp.json().get("text", "")
#
#     async def close(self):
#         await self.client.aclose()
