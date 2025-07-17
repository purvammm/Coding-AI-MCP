import asyncio
from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime

from config import Config, ModelConfig
from models import ModelProvider, OllamaProvider, HuggingFaceProvider, GroqProvider, TogetherProvider
from models.base import ChatMessage, ModelResponse
from .file_manager import FileManager
from .terminal_manager import TerminalManager
from .project_indexer import ProjectIndexer
from .attachment_manager import AttachmentManager, AttachmentContext
from .context_manager import ContextManager

class MCPAgent:
    """Main MCP AI Coding Agent"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = workspace_path
        
        # Initialize components
        self.file_manager = FileManager(workspace_path)
        self.terminal_manager = TerminalManager(workspace_path)
        self.project_indexer = ProjectIndexer(workspace_path)
        self.attachment_manager = AttachmentManager(workspace_path)
        self.context_manager = ContextManager()
        
        # Initialize model providers
        self.providers: Dict[str, ModelProvider] = {}
        self._init_providers()
        
        # Current session state
        self.current_model: Optional[ModelConfig] = None
        self.conversation_history: List[ChatMessage] = []
        
    def _init_providers(self):
        """Initialize AI model providers"""
        # Ollama (local)
        self.providers['ollama'] = OllamaProvider()
        
        # API-based providers (if API keys available)
        if Config.GROQ_API_KEY:
            self.providers['groq'] = GroqProvider(Config.GROQ_API_KEY)
        
        if Config.HUGGINGFACE_API_KEY:
            self.providers['huggingface'] = HuggingFaceProvider(Config.HUGGINGFACE_API_KEY)
        
        if Config.TOGETHER_API_KEY:
            self.providers['together'] = TogetherProvider(Config.TOGETHER_API_KEY)
    
    async def initialize(self):
        """Initialize the agent and build project index"""
        print("Initializing MCP AI Agent...")
        
        # Build project index
        await self.project_indexer.build_index()
        
        # Check provider availability
        available_providers = []
        for name, provider in self.providers.items():
            if await provider.health_check():
                available_providers.append(name)
        
        print(f"Available providers: {available_providers}")
        
        # Set default model if available
        available_models = Config.get_available_models()
        if available_models:
            self.current_model = available_models[0]
            print(f"Default model: {self.current_model.name}")
    
    async def set_model(self, model_name: str) -> bool:
        """Set the current AI model"""
        model = Config.get_model_by_name(model_name)
        if not model:
            return False
        
        # Check if provider is available
        provider = self.providers.get(model.provider)
        if not provider or not await provider.health_check():
            return False
        
        self.current_model = model
        return True
    
    async def chat(
        self,
        message: str,
        stream: bool = False,
        attachment_ids: List[str] = None
    ) -> AsyncGenerator[str, None]:
        """Chat with the AI agent with attachment support"""
        if not self.current_model:
            yield "Error: No model selected"
            return

        provider = self.providers.get(self.current_model.provider)
        if not provider:
            yield "Error: Provider not available"
            return

        # Get relevant attachments
        attachment_contexts = []
        if attachment_ids:
            for attachment_id in attachment_ids:
                attachment = self.attachment_manager.get_attachment(attachment_id)
                if attachment:
                    attachment_contexts.append(AttachmentContext(
                        attachment=attachment,
                        relevance_score=1.0,
                        summary=f"File: {attachment.original_filename}\nContent: {attachment.extracted_text[:500] if attachment.extracted_text else 'No text extracted'}"
                    ))

        # Also search for relevant attachments based on message content
        relevant_attachments = self.attachment_manager.get_relevant_attachments(message, limit=3)
        attachment_contexts.extend(relevant_attachments)

        # Create user message
        user_message = ChatMessage(role="user", content=message)

        # Get optimized context window
        context_window = await self.context_manager.get_context_window(
            message, attachment_contexts
        )

        # Prepare messages with enhanced context
        messages = await self._prepare_enhanced_messages(
            user_message, context_window, attachment_contexts
        )

        try:
            if stream:
                # Stream response
                response_content = ""
                async for chunk in provider.stream_response(
                    messages,
                    self.current_model.model_id,
                    self.current_model.max_tokens,
                    self.current_model.temperature
                ):
                    response_content += chunk
                    yield chunk

                # Add to context manager
                assistant_message = ChatMessage(role="assistant", content=response_content)
                self.context_manager.add_conversation_turn(
                    user_message, assistant_message, attachment_ids
                )
            else:
                # Get full response
                response = await provider.generate_response(
                    messages,
                    self.current_model.model_id,
                    self.current_model.max_tokens,
                    self.current_model.temperature
                )

                # Add to context manager
                assistant_message = ChatMessage(role="assistant", content=response.content)
                self.context_manager.add_conversation_turn(
                    user_message, assistant_message, attachment_ids
                )

                yield response.content

        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            yield error_msg
    
    async def _prepare_enhanced_messages(
        self,
        user_message: ChatMessage,
        context_window: Any,
        attachment_contexts: List[AttachmentContext]
    ) -> List[ChatMessage]:
        """Prepare messages with enhanced context management"""
        # Get project context
        project_summary = self.project_indexer.get_project_summary()

        # Build system message with all context
        system_parts = [
            "You are an AI coding assistant with access to the following tools:",
            "",
            "1. File Operations: Read, write, edit, delete files",
            "2. Terminal Commands: Execute commands with safety checks",
            "3. Project Analysis: Understand project structure and code",
            "4. Attachment Analysis: Process uploaded documents, images, and files",
            "",
            f"Current Project Context:",
            f"- Total files: {project_summary.get('total_files', 0)}",
            f"- Total lines: {project_summary.get('total_lines', 0)}",
            f"- Languages: {project_summary.get('languages', {})}",
            f"- Symbols indexed: {project_summary.get('symbol_count', 0)}"
        ]

        # Add conversation summary if available
        if context_window.summary:
            system_parts.extend([
                "",
                "Previous Conversation Summary:",
                context_window.summary
            ])

        # Add key points if available
        if context_window.key_points:
            system_parts.extend([
                "",
                "Key Points from Previous Discussion:",
                *[f"- {point}" for point in context_window.key_points[:5]]
            ])

        # Add attachment context
        if attachment_contexts:
            system_parts.extend([
                "",
                "Available Reference Materials:"
            ])
            for ctx in attachment_contexts:
                system_parts.extend([
                    f"- {ctx.attachment.original_filename} ({ctx.attachment.file_type})",
                    f"  {ctx.summary[:200]}..."
                ])

        system_parts.extend([
            "",
            "You can help with:",
            "- Code generation and editing",
            "- Running tests and builds",
            "- Installing dependencies",
            "- Analyzing code structure",
            "- Debugging issues",
            "- Project setup and configuration",
            "- Processing and analyzing uploaded documents",
            "",
            "Always ask for confirmation before:",
            "- Deleting files",
            "- Running potentially dangerous commands",
            "- Making significant changes to project structure",
            "",
            "Be helpful, accurate, and safe in your responses."
        ])

        system_content = "\n".join(system_parts)
        system_message = ChatMessage(role="system", content=system_content)

        # Use context window messages + current user message
        messages = [system_message] + context_window.messages + [user_message]

        return messages
    
    async def execute_file_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute file operation"""
        try:
            if operation == "read":
                content = await self.file_manager.read_file(kwargs['path'])
                return {"success": True, "content": content}
            
            elif operation == "write":
                success = await self.file_manager.write_file(
                    kwargs['path'], 
                    kwargs['content'],
                    kwargs.get('create_backup', True)
                )
                return {"success": success}
            
            elif operation == "delete":
                success = await self.file_manager.delete_file(
                    kwargs['path'],
                    kwargs.get('create_backup', True)
                )
                return {"success": success}
            
            elif operation == "list":
                files = await self.file_manager.list_files(
                    kwargs.get('path', '.'),
                    kwargs.get('include_hidden', False)
                )
                return {"success": True, "files": [f.__dict__ for f in files]}
            
            elif operation == "move":
                success = await self.file_manager.move_file(
                    kwargs['source'],
                    kwargs['destination']
                )
                return {"success": success}
            
            elif operation == "copy":
                success = await self.file_manager.copy_file(
                    kwargs['source'],
                    kwargs['destination']
                )
                return {"success": success}
            
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_terminal_command(self, command: str, auto_approve: bool = False, stream: bool = False):
        """Execute terminal command"""
        try:
            if stream:
                async for output in self.terminal_manager.execute_command_stream(
                    command, auto_approve
                ):
                    yield output
            else:
                result = await self.terminal_manager.execute_command(
                    command, auto_approve
                )
                yield {
                    "success": True,
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "execution_time": result.execution_time
                }
        except Exception as e:
            yield {"success": False, "error": str(e)}
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        available_models = Config.get_available_models()
        return [
            {
                "name": model.name,
                "provider": model.provider,
                "description": model.description,
                "max_tokens": model.max_tokens,
                "requires_api_key": model.requires_api_key
            }
            for model in available_models
        ]
    
    def get_current_model(self) -> Optional[Dict[str, Any]]:
        """Get current model info"""
        if not self.current_model:
            return None
        
        return {
            "name": self.current_model.name,
            "provider": self.current_model.provider,
            "description": self.current_model.description,
            "max_tokens": self.current_model.max_tokens
        }
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversation_history
        ]
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    async def search_code(self, query: str, symbol_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for code symbols"""
        symbols = self.project_indexer.search_symbols(query, symbol_type)
        return [
            {
                "name": symbol.name,
                "type": symbol.type,
                "file_path": symbol.file_path,
                "line_number": symbol.line_number,
                "docstring": symbol.docstring,
                "parameters": symbol.parameters,
                "parent": symbol.parent
            }
            for symbol in symbols
        ]

    async def upload_attachment(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Upload and process an attachment"""
        try:
            attachment = await self.attachment_manager.upload_attachment(
                file_content, filename, extract_content=True
            )
            return {
                "success": True,
                "attachment": {
                    "id": attachment.id,
                    "filename": attachment.original_filename,
                    "file_type": attachment.file_type,
                    "size": attachment.size,
                    "upload_time": attachment.upload_time.isoformat(),
                    "has_extracted_text": bool(attachment.extracted_text),
                    "has_thumbnail": bool(attachment.thumbnail_path)
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_attachments(self) -> List[Dict[str, Any]]:
        """Get list of all attachments"""
        attachments = self.attachment_manager.list_attachments()
        return [
            {
                "id": att.id,
                "filename": att.original_filename,
                "file_type": att.file_type,
                "size": att.size,
                "upload_time": att.upload_time.isoformat(),
                "has_extracted_text": bool(att.extracted_text),
                "has_thumbnail": bool(att.thumbnail_path)
            }
            for att in attachments
        ]

    async def get_attachment_content(self, attachment_id: str) -> Dict[str, Any]:
        """Get attachment content and metadata"""
        attachment = self.attachment_manager.get_attachment(attachment_id)
        if not attachment:
            return {"success": False, "error": "Attachment not found"}

        return {
            "success": True,
            "attachment": {
                "id": attachment.id,
                "filename": attachment.original_filename,
                "file_type": attachment.file_type,
                "size": attachment.size,
                "upload_time": attachment.upload_time.isoformat(),
                "extracted_text": attachment.extracted_text,
                "metadata": attachment.metadata,
                "thumbnail_path": attachment.thumbnail_path
            }
        }

    async def delete_attachment(self, attachment_id: str) -> Dict[str, Any]:
        """Delete an attachment"""
        success = await self.attachment_manager.delete_attachment(attachment_id)
        return {"success": success}

    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation and context statistics"""
        return self.context_manager.get_conversation_stats()

    async def summarize_conversation(self) -> Dict[str, Any]:
        """Get conversation summary and context info"""
        stats = self.context_manager.get_conversation_stats()

        # Get recent context window for analysis
        context_window = await self.context_manager.get_context_window("summary")

        return {
            "stats": stats,
            "current_context_tokens": context_window.total_tokens,
            "key_points": context_window.key_points,
            "summary": context_window.summary
        }
