from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncGenerator, Any
from dataclasses import dataclass
import asyncio

@dataclass
class ChatMessage:
    role: str  # 'user', 'assistant', 'system'
    content: str
    
@dataclass
class ModelResponse:
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None

class ModelProvider(ABC):
    """Abstract base class for AI model providers"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[ChatMessage],
        model_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stream: bool = False
    ) -> ModelResponse:
        """Generate a response from the model"""
        pass
    
    @abstractmethod
    async def stream_response(
        self,
        messages: List[ChatMessage],
        model_id: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream response from the model"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is available"""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models for this provider"""
        pass
    
    def format_messages(self, messages: List[ChatMessage]) -> Any:
        """Format messages for the specific provider"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    async def health_check(self) -> bool:
        """Perform a health check on the provider"""
        try:
            return await self.is_available()
        except Exception:
            return False
