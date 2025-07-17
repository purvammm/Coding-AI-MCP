import asyncio
import aiohttp
import json
from typing import List, AsyncGenerator, Optional
from .base import ModelProvider, ChatMessage, ModelResponse

class OllamaProvider(ModelProvider):
    """Ollama local model provider"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        super().__init__()
        self.base_url = base_url
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        model_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stream: bool = False
    ) -> ModelResponse:
        """Generate a response from Ollama"""
        
        # Convert messages to Ollama format
        prompt = self._messages_to_prompt(messages)
        
        payload = {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return ModelResponse(
                            content=result.get("response", ""),
                            model=model_id,
                            finish_reason="stop"
                        )
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {response.status} - {error_text}")
        except Exception as e:
            raise Exception(f"Failed to generate response from Ollama: {str(e)}")
    
    async def stream_response(
        self,
        messages: List[ChatMessage],
        model_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream response from Ollama"""
        
        prompt = self._messages_to_prompt(messages)
        
        payload = {
            "model": model_id,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        async for line in response.content:
                            if line:
                                try:
                                    data = json.loads(line.decode('utf-8'))
                                    if 'response' in data:
                                        yield data['response']
                                    if data.get('done', False):
                                        break
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {response.status} - {error_text}")
        except Exception as e:
            raise Exception(f"Failed to stream response from Ollama: {str(e)}")
    
    async def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except:
            return False
    
    async def list_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model["name"] for model in data.get("models", [])]
                    return []
        except:
            return []
    
    def _messages_to_prompt(self, messages: List[ChatMessage]) -> str:
        """Convert chat messages to a single prompt for Ollama"""
        prompt_parts = []
        
        for message in messages:
            if message.role == "system":
                prompt_parts.append(f"System: {message.content}")
            elif message.role == "user":
                prompt_parts.append(f"User: {message.content}")
            elif message.role == "assistant":
                prompt_parts.append(f"Assistant: {message.content}")
        
        prompt_parts.append("Assistant:")
        return "\n\n".join(prompt_parts)
