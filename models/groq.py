import aiohttp
import json
from typing import List, AsyncGenerator, Optional
from .base import ModelProvider, ChatMessage, ModelResponse

class GroqProvider(ModelProvider):
    """Groq API provider for fast inference"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.groq.com/openai/v1"
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        model_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stream: bool = False
    ) -> ModelResponse:
        """Generate a response from Groq"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_id,
            "messages": self.format_messages(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        choice = result["choices"][0]
                        return ModelResponse(
                            content=choice["message"]["content"],
                            model=model_id,
                            usage=result.get("usage"),
                            finish_reason=choice.get("finish_reason")
                        )
                    else:
                        error_text = await response.text()
                        raise Exception(f"Groq API error: {response.status} - {error_text}")
        except Exception as e:
            raise Exception(f"Failed to generate response from Groq: {str(e)}")
    
    async def stream_response(
        self,
        messages: List[ChatMessage],
        model_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream response from Groq"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_id,
            "messages": self.format_messages(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        async for line in response.content:
                            if line:
                                line_str = line.decode('utf-8').strip()
                                if line_str.startswith('data: '):
                                    data_str = line_str[6:]
                                    if data_str == '[DONE]':
                                        break
                                    try:
                                        data = json.loads(data_str)
                                        if 'choices' in data and len(data['choices']) > 0:
                                            delta = data['choices'][0].get('delta', {})
                                            if 'content' in delta:
                                                yield delta['content']
                                    except json.JSONDecodeError:
                                        continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"Groq API error: {response.status} - {error_text}")
        except Exception as e:
            raise Exception(f"Failed to stream response from Groq: {str(e)}")
    
    async def is_available(self) -> bool:
        """Check if Groq API is available"""
        if not self.api_key:
            return False
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
        except:
            return False
    
    async def list_models(self) -> List[str]:
        """List available Groq models"""
        if not self.api_key:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model["id"] for model in data.get("data", [])]
                    return []
        except:
            return []
