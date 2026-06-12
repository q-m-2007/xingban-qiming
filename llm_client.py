"""
LLM客户端封装
统一调用接口，支持DeepSeek/通义千问/文心一言
"""

import os
import json
import re
import logging
import asyncio
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str = "deepseek"
    api_key: str = ""
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    max_tokens: int = 500
    temperature: float = 0.7
    timeout: int = 30
    max_retries: int = 3


class LLMClient:
    """统一LLM客户端"""

    def __init__(self, config: Optional[LLMConfig] = None):
        if config is None:
            config = LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "deepseek"),
                api_key=os.getenv("LLM_API_KEY", ""),
                model=os.getenv("LLM_MODEL", "deepseek-chat"),
                base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "500")),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            )
        self.config = config
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self._client

    async def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> str:
        """调用LLM生成回复（带重试）"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        temp = temperature if temperature is not None else self.config.temperature

        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = await self._call_api(messages, temp)
                return response
            except Exception as e:
                last_error = e
                logger.warning(f"LLM调用失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))

        raise LLMError(f"LLM调用失败，已重试{self.config.max_retries}次: {last_error}")

    async def chat_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """调用LLM并解析JSON响应"""
        response = await self.chat(prompt, system, temperature)
        return self._parse_json(response)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """健壮的JSON解析"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取```json ... ```中的内容
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试提取第一个JSON对象
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise LLMError(f"无法解析LLM返回的JSON: {text[:200]}")

    async def _call_api(self, messages: list, temperature: float) -> str:
        """调用API"""
        url = f"{self.config.base_url}/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }

        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": temperature,
            "stream": False
        }

        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise LLMError("API速率限制，请稍后重试")
            raise LLMError(f"API HTTP错误 {e.response.status_code}: {e.response.text[:200]}")
        except httpx.RequestError as e:
            raise LLMError(f"API请求失败: {str(e)}")
        except (KeyError, IndexError) as e:
            raise LLMError(f"API响应格式错误: {str(e)}")

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None


class LLMError(Exception):
    """LLM调用异常"""
    pass
