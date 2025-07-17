import aiohttp
import json
from typing import List, AsyncGenerator, Optional
from .base import ModelProvider, ChatMessage, ModelResponse

class MoonshotProvider(ModelProvider):
    """Moonshot Kimi AI provider for agentic AI capabilities"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.moonshot.cn/v1"
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        model_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stream: bool = False
    ) -> ModelResponse:
        """Generate a response from Moonshot Kimi"""
        
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
                    timeout=aiohttp.ClientTimeout(total=120)
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
                        raise Exception(f"Moonshot API error: {response.status} - {error_text}")
        except Exception as e:
            raise Exception(f"Failed to generate response from Moonshot: {str(e)}")
    
    async def stream_response(
        self,
        messages: List[ChatMessage],
        model_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream response from Moonshot Kimi"""
        
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
                    timeout=aiohttp.ClientTimeout(total=120)
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
                        raise Exception(f"Moonshot API error: {response.status} - {error_text}")
        except Exception as e:
            raise Exception(f"Failed to stream response from Moonshot: {str(e)}")
    
    async def is_available(self) -> bool:
        """Check if Moonshot API is available"""
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
        """List available Moonshot models"""
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
    
    async def web_search(self, query: str, num_results: int = 5) -> List[dict]:
        """Perform web search using Moonshot's web search capabilities"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Use Moonshot's web search feature if available
        payload = {
            "model": "moonshot-v1-128k",  # Use the model that supports web search
            "messages": [
                {
                    "role": "system",
                    "content": "You are a web search assistant. Search for information and provide structured results."
                },
                {
                    "role": "user", 
                    "content": f"Search the web for: {query}. Provide {num_results} relevant results with titles, URLs, and summaries."
                }
            ],
            "tools": [
                {
                    "type": "web_search",
                    "web_search": {
                        "enable": True
                    }
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.3
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
                        # Parse the response to extract search results
                        content = result["choices"][0]["message"]["content"]
                        
                        # This is a simplified parser - in practice, you'd need to 
                        # parse the structured response from Moonshot's web search
                        return [
                            {
                                "title": "Search Result",
                                "url": "https://example.com",
                                "snippet": content[:200] + "..."
                            }
                        ]
                    else:
                        return []
        except Exception as e:
            print(f"Web search error: {e}")
            return []
    
    async def analyze_url(self, url: str) -> dict:
        """Analyze content from a URL using Moonshot's capabilities"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "moonshot-v1-128k",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a web content analyzer. Analyze the content from the given URL and provide a structured summary."
                },
                {
                    "role": "user",
                    "content": f"Analyze and summarize the content from this URL: {url}"
                }
            ],
            "tools": [
                {
                    "type": "web_search",
                    "web_search": {
                        "enable": True
                    }
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.3
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
                        content = result["choices"][0]["message"]["content"]
                        
                        return {
                            "url": url,
                            "title": "Analyzed Content",
                            "content": content,
                            "summary": content[:500] + "..." if len(content) > 500 else content
                        }
                    else:
                        return {"error": f"Failed to analyze URL: {response.status}"}
        except Exception as e:
            return {"error": f"URL analysis error: {str(e)}"}
    
    def format_messages(self, messages: List[ChatMessage]) -> List[dict]:
        """Format messages for Moonshot API"""
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg.role,
                "content": msg.content
            })
        return formatted
