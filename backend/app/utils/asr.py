"""
ASR 客户端封装（预留）

TODO: 接入 ASR 服务用于语音转文字
"""

# import httpx
# from typing import Optional

# class ASRClient:
#     """自动语音识别客户端"""
#
#     def __init__(self, base_url: str = "http://localhost:5001"):
#         self.base_url = base_url
#         self.client = httpx.AsyncClient(timeout=60)
#
#     async def transcribe(self, audio_bytes: bytes) -> str:
#         """将音频转为文字"""
#         resp = await self.client.post(
#             f"{self.base_url}/asr",
#             files={"audio": audio_bytes},
#         )
#         resp.raise_for_status()
#         return resp.json().get("text", "")
#
#     async def close(self):
#         await self.client.aclose()
