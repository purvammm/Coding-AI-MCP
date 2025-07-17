import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ModelConfig:
    name: str
    provider: str
    model_id: str
    max_tokens: int
    temperature: float = 0.7
    requires_api_key: bool = False
    api_key_env: Optional[str] = None
    description: str = ""

class Config:
    # Server settings
    HOST = "localhost"
    PORT = 8000
    DEBUG = True
    
    # File operations settings
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    BACKUP_DIR = ".mcp_backups"
    ALLOWED_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
        '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.r',
        '.sql', '.html', '.css', '.scss', '.sass', '.less', '.xml', '.json',
        '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.md', '.txt',
        '.sh', '.bat', '.ps1', '.dockerfile', '.gitignore', '.env'
    }
    
    # Terminal settings
    TERMINAL_TIMEOUT = 30  # seconds

    # Security settings - can be disabled for security analysis
    ENABLE_COMMAND_VALIDATION = os.getenv("ENABLE_COMMAND_VALIDATION", "true").lower() == "true"
    ENABLE_DANGEROUS_COMMAND_DETECTION = os.getenv("ENABLE_DANGEROUS_COMMAND_DETECTION", "true").lower() == "true"
    ENABLE_PATH_VALIDATION = os.getenv("ENABLE_PATH_VALIDATION", "true").lower() == "true"
    ENABLE_FILE_EXTENSION_VALIDATION = os.getenv("ENABLE_FILE_EXTENSION_VALIDATION", "true").lower() == "true"

    # Security analysis mode - disables most restrictions
    SECURITY_ANALYSIS_MODE = os.getenv("SECURITY_ANALYSIS_MODE", "false").lower() == "true"

    DANGEROUS_COMMANDS = {
        'rm', 'del', 'rmdir', 'format', 'fdisk', 'mkfs', 'dd',
        'shutdown', 'reboot', 'halt', 'poweroff', 'init',
        'sudo rm', 'sudo del', 'sudo rmdir'
    }
    
    # AI Models configuration
    MODELS: List[ModelConfig] = [
        # Local Ollama models
        ModelConfig(
            name="CodeLlama 7B",
            provider="ollama",
            model_id="codellama:7b",
            max_tokens=4096,
            description="Meta's CodeLlama 7B - Good for code generation and completion"
        ),
        ModelConfig(
            name="CodeLlama 13B",
            provider="ollama", 
            model_id="codellama:13b",
            max_tokens=4096,
            description="Meta's CodeLlama 13B - Better performance than 7B"
        ),
        ModelConfig(
            name="Qwen2.5-Coder 1.5B",
            provider="ollama",
            model_id="qwen2.5-coder:1.5b",
            max_tokens=8192,
            description="Alibaba's Qwen2.5-Coder 1.5B - Fast and efficient for coding"
        ),
        ModelConfig(
            name="Qwen2.5-Coder 7B",
            provider="ollama",
            model_id="qwen2.5-coder:7b",
            max_tokens=8192,
            description="Alibaba's Qwen2.5-Coder 7B - Excellent coding capabilities"
        ),
        ModelConfig(
            name="Qwen2.5-Coder 14B",
            provider="ollama",
            model_id="qwen2.5-coder:14b",
            max_tokens=8192,
            description="Alibaba's Qwen2.5-Coder 14B - High performance coding model"
        ),
        ModelConfig(
            name="Mistral 7B",
            provider="ollama",
            model_id="mistral:7b",
            max_tokens=8192,
            description="Mistral 7B - General purpose model with good coding abilities"
        ),
        ModelConfig(
            name="Llama 3 8B",
            provider="ollama",
            model_id="llama3:8b",
            max_tokens=8192,
            description="Meta's Llama 3 8B - Latest Llama model"
        ),
        ModelConfig(
            name="DeepSeek Coder 6.7B",
            provider="ollama",
            model_id="deepseek-coder:6.7b",
            max_tokens=4096,
            description="DeepSeek Coder 6.7B - Specialized for coding tasks"
        ),
        
        # API-based models
        ModelConfig(
            name="Llama 3 70B (Groq)",
            provider="groq",
            model_id="llama3-70b-8192",
            max_tokens=8192,
            requires_api_key=True,
            api_key_env="GROQ_API_KEY",
            description="Meta's Llama 3 70B via Groq - Fast inference"
        ),
        ModelConfig(
            name="Mixtral 8x7B (Groq)",
            provider="groq",
            model_id="mixtral-8x7b-32768",
            max_tokens=32768,
            requires_api_key=True,
            api_key_env="GROQ_API_KEY",
            description="Mistral's Mixtral 8x7B via Groq - High performance"
        ),
        ModelConfig(
            name="CodeLlama 34B (Together)",
            provider="together",
            model_id="codellama/CodeLlama-34b-Instruct-hf",
            max_tokens=4096,
            requires_api_key=True,
            api_key_env="TOGETHER_API_KEY",
            description="Meta's CodeLlama 34B via Together AI"
        ),
        ModelConfig(
            name="Qwen2.5-Coder 32B (HF)",
            provider="huggingface",
            model_id="Qwen/Qwen2.5-Coder-32B-Instruct",
            max_tokens=8192,
            requires_api_key=True,
            api_key_env="HUGGINGFACE_API_KEY",
            description="Alibaba's Qwen2.5-Coder 32B via Hugging Face"
        ),
    ]
    
    @classmethod
    def get_model_by_name(cls, name: str) -> Optional[ModelConfig]:
        for model in cls.MODELS:
            if model.name == name:
                return model
        return None
    
    @classmethod
    def get_available_models(cls) -> List[ModelConfig]:
        """Get list of available models based on API keys and local installations"""
        available = []
        for model in cls.MODELS:
            if model.requires_api_key:
                if model.api_key_env and os.getenv(model.api_key_env):
                    available.append(model)
            else:
                # For local models, we'll assume they're available
                # In a real implementation, you'd check if Ollama is running
                available.append(model)
        return available

# Environment variables
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")
