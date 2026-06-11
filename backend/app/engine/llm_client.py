"""
LLM调用封装
支持多种LLM提供商，统一接口
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import httpx


class LLMClient(ABC):
    """LLM客户端基类"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    async def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """生成结构化输出"""
        pass


class OpenAIClient(LLMClient):
    """OpenAI兼容客户端（支持GPT-4o-mini、Qwen等）"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
        timeout: float = 30.0
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("API key is required")
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1000)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"LLM API error: {response.status_code} - {response.text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """生成结构化输出"""
        # 在prompt中添加JSON格式要求
        structured_prompt = f"""{prompt}

请严格按照以下JSON格式返回，不要添加任何其他内容：
```json
{json.dumps(schema, ensure_ascii=False, indent=2)}
```"""
        
        response = await self.generate(structured_prompt, **kwargs)
        
        # 提取JSON
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试从markdown代码块中提取
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
            if json_match:
                return json.loads(json_match.group(1))
            raise ValueError(f"Failed to parse JSON from response: {response[:200]}")


class QwenClient(OpenAIClient):
    """通义千问客户端"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen-plus"):
        super().__init__(
            api_key=api_key or os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=model
        )


class DeepSeekClient(OpenAIClient):
    """DeepSeek客户端"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        super().__init__(
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            model=model
        )


class LLMFactory:
    """LLM工厂类"""
    
    @staticmethod
    def create_client(
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> LLMClient:
        """创建LLM客户端"""
        if provider == "openai":
            return OpenAIClient(
                api_key=api_key,
                model=model or "gpt-4o-mini",
                **kwargs
            )
        elif provider == "qwen":
            return QwenClient(
                api_key=api_key,
                model=model or "qwen-plus",
                **kwargs
            )
        elif provider == "deepseek":
            return DeepSeekClient(
                api_key=api_key,
                model=model or "deepseek-chat",
                **kwargs
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")


# 默认客户端（单例）
_default_client: Optional[LLMClient] = None


async def get_default_client() -> LLMClient:
    """获取默认LLM客户端"""
    global _default_client
    if _default_client is None:
        # 优先使用DeepSeek
        if os.getenv("DEEPSEEK_API_KEY"):
            _default_client = LLMFactory.create_client("deepseek")
        elif os.getenv("DASHSCOPE_API_KEY"):
            _default_client = LLMFactory.create_client("qwen")
        else:
            _default_client = LLMFactory.create_client("openai")
    return _default_client


async def generate_text(prompt: str, **kwargs) -> str:
    """便捷函数：生成文本"""
    client = await get_default_client()
    return await client.generate(prompt, **kwargs)


async def generate_structured(prompt: str, schema: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """便捷函数：生成结构化输出"""
    client = await get_default_client()
    return await client.generate_structured(prompt, schema, **kwargs)
