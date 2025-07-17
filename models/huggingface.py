import aiohttp
import json
from typing import List, AsyncGenerator, Optional
from .base import ModelProvider, ChatMessage, ModelResponse

class HuggingFaceProvider(ModelProvider):
    """Hugging Face Inference API provider"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api-inference.huggingface.co/models"
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        model_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stream: bool = False
    ) -> ModelResponse:
        """Generate a response from Hugging Face"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert messages to prompt format
        prompt = self._messages_to_prompt(messages)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/{model_id}",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if isinstance(result, list) and len(result) > 0:
                            generated_text = result[0].get("generated_text", "")
                            return ModelResponse(
                                content=generated_text,
                                model=model_id,
                                finish_reason="stop"
                            )
                        else:
                            raise Exception("Unexpected response format from Hugging Face")
                    else:
                        error_text = await response.text()
                        if response.status == 503:
                            raise Exception("Model is loading, please try again in a few minutes")
                        raise Exception(f"Hugging Face API error: {response.status} - {error_text}")
        except Exception as e:
            raise Exception(f"Failed to generate response from Hugging Face: {str(e)}")
    
    async def stream_response(
        self,
        messages: List[ChatMessage],
        model_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream response from Hugging Face (simulated streaming)"""
        
        # Hugging Face Inference API doesn't support streaming for most models
        # So we'll simulate it by generating the full response and yielding chunks
        response = await self.generate_response(messages, model_id, max_tokens, temperature)
        
        # Yield the response in chunks to simulate streaming
        content = response.content
        chunk_size = 10  # characters per chunk
        
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            yield chunk
            # Small delay to simulate streaming
            import asyncio
            await asyncio.sleep(0.05)
    
    async def is_available(self) -> bool:
        """Check if Hugging Face API is available"""
        if not self.api_key:
            return False
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # Test with a simple model
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/gpt2",
                    headers=headers,
                    json={"inputs": "test"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status in [200, 503]  # 503 means model is loading
        except:
            return False
    
    async def list_models(self) -> List[str]:
        """List available Hugging Face models (predefined list)"""
        # Hugging Face has thousands of models, so we'll return a curated list
        # of popular coding models
        return [
            "Qwen/Qwen2.5-Coder-32B-Instruct",
            "Qwen/Qwen2.5-Coder-14B-Instruct",
            "Qwen/Qwen2.5-Coder-7B-Instruct",
            "deepseek-ai/deepseek-coder-33b-instruct",
            "deepseek-ai/deepseek-coder-6.7b-instruct",
            "WizardLM/WizardCoder-Python-34B-V1.0",
            "WizardLM/WizardCoder-15B-V1.0",
            "microsoft/DialoGPT-medium",
            "microsoft/CodeBERT-base",
            "Salesforce/codegen-350M-mono"
        ]
    
    def _messages_to_prompt(self, messages: List[ChatMessage]) -> str:
        """Convert chat messages to a single prompt for Hugging Face"""
        prompt_parts = []
        
        for message in messages:
            if message.role == "system":
                prompt_parts.append(f"### System\n{message.content}")
            elif message.role == "user":
                prompt_parts.append(f"### User\n{message.content}")
            elif message.role == "assistant":
                prompt_parts.append(f"### Assistant\n{message.content}")
        
        prompt_parts.append("### Assistant\n")
        return "\n\n".join(prompt_parts)
