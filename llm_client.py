"""
LLM客户端封装
统一调用接口，支持DeepSeek/通义千问/文心一言
"""

import os
import json
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass


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
        """
        调用LLM生成回复

        Args:
            prompt: 用户消息
            system: 系统提示词
            temperature: 温度参数

        Returns:
            LLM回复文本
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        temp = temperature if temperature is not None else self.config.temperature

        try:
            response = await self._call_api(messages, temp)
            return response
        except Exception as e:
            raise LLMError(f"LLM调用失败: {str(e)}")

    async def chat_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        调用LLM并解析JSON响应

        Args:
            prompt: 用户消息（应要求返回JSON）
            system: 系统提示词
            temperature: 温度参数

        Returns:
            解析后的JSON对象
        """
        response = await self.chat(prompt, system, temperature)

        # 尝试提取JSON
        try:
            # 先尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取```json ... ```中的内容
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            else:
                raise LLMError(f"无法解析LLM返回的JSON: {response[:200]}")

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
