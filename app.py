import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import Config
from core.agent import MCPAgent

# Pydantic models for API
class ChatRequest(BaseModel):
    message: str
    stream: bool = True
    attachment_ids: Optional[List[str]] = None

class FileOperationRequest(BaseModel):
    operation: str
    path: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    create_backup: bool = True
    include_hidden: bool = False

class TerminalCommandRequest(BaseModel):
    command: str
    auto_approve: bool = False
    stream: bool = True

class ModelSelectionRequest(BaseModel):
    model_name: str

class SearchRequest(BaseModel):
    query: str
    symbol_type: Optional[str] = None

class WebSearchRequest(BaseModel):
    query: str
    num_results: int = 10
    provider: Optional[str] = None
    include_content: bool = False

class UrlScrapeRequest(BaseModel):
    url: str
    use_cache: bool = True

# Initialize FastAPI app
app = FastAPI(title="MCP AI Coding Agent", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = MCPAgent()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup"""
    await agent.initialize()

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main HTML page"""
    return FileResponse("static/index.html")

@app.get("/api/models")
async def get_models():
    """Get available AI models"""
    return {"models": agent.get_available_models()}

@app.get("/api/current-model")
async def get_current_model():
    """Get current selected model"""
    return {"model": agent.get_current_model()}

@app.post("/api/select-model")
async def select_model(request: ModelSelectionRequest):
    """Select AI model"""
    success = await agent.set_model(request.model_name)
    if success:
        return {"success": True, "model": agent.get_current_model()}
    else:
        raise HTTPException(status_code=400, detail="Failed to select model")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat with AI (non-streaming)"""
    if request.stream:
        raise HTTPException(status_code=400, detail="Use WebSocket for streaming chat")
    
    response_content = ""
    async for chunk in agent.chat(request.message, stream=False):
        response_content += chunk
    
    return {"response": response_content}

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat":
                message = message_data.get("message", "")
                attachment_ids = message_data.get("attachment_ids", [])

                # Send response chunks
                async for chunk in agent.chat(message, stream=True, attachment_ids=attachment_ids):
                    await manager.send_personal_message(
                        json.dumps({"type": "chat_chunk", "content": chunk}),
                        websocket
                    )
                
                # Send end marker
                await manager.send_personal_message(
                    json.dumps({"type": "chat_end"}),
                    websocket
                )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/file-operation")
async def file_operation(request: FileOperationRequest):
    """Execute file operation"""
    result = await agent.execute_file_operation(
        request.operation,
        path=request.path,
        content=request.content,
        source=request.source,
        destination=request.destination,
        create_backup=request.create_backup,
        include_hidden=request.include_hidden
    )
    return result

@app.post("/api/terminal-command")
async def terminal_command(request: TerminalCommandRequest):
    """Execute terminal command (non-streaming)"""
    if request.stream:
        raise HTTPException(status_code=400, detail="Use WebSocket for streaming commands")
    
    result = None
    async for output in agent.execute_terminal_command(
        request.command, 
        request.auto_approve, 
        stream=False
    ):
        result = output
    
    return result

@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    """WebSocket endpoint for streaming terminal commands"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            command_data = json.loads(data)
            
            if command_data.get("type") == "command":
                command = command_data.get("command", "")
                auto_approve = command_data.get("auto_approve", False)
                
                # Send command output
                async for output in agent.execute_terminal_command(
                    command, auto_approve, stream=True
                ):
                    await manager.send_personal_message(
                        json.dumps({"type": "terminal_output", "content": output}),
                        websocket
                    )
                
                # Send end marker
                await manager.send_personal_message(
                    json.dumps({"type": "terminal_end"}),
                    websocket
                )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/conversation-history")
async def get_conversation_history():
    """Get conversation history"""
    return {"history": agent.get_conversation_history()}

@app.post("/api/clear-conversation")
async def clear_conversation():
    """Clear conversation history"""
    agent.clear_conversation()
    return {"success": True}

@app.post("/api/search-code")
async def search_code(request: SearchRequest):
    """Search code symbols"""
    results = await agent.search_code(request.query, request.symbol_type)
    return {"results": results}

@app.get("/api/project-summary")
async def get_project_summary():
    """Get project summary"""
    return agent.project_indexer.get_project_summary()

@app.get("/api/file-operations-log")
async def get_file_operations_log():
    """Get file operations log"""
    return {"log": agent.file_manager.get_operation_log()}

@app.get("/api/terminal-history")
async def get_terminal_history():
    """Get terminal command history"""
    return {"history": agent.terminal_manager.get_command_history()}

@app.get("/api/running-processes")
async def get_running_processes():
    """Get running processes"""
    return {"processes": agent.terminal_manager.get_running_processes()}

@app.post("/api/kill-process/{pid}")
async def kill_process(pid: int):
    """Kill a running process"""
    success = await agent.terminal_manager.kill_process(pid)
    return {"success": success}

@app.post("/api/rebuild-index")
async def rebuild_index():
    """Rebuild project index"""
    await agent.project_indexer.build_index(force_rebuild=True)
    return {"success": True, "summary": agent.project_indexer.get_project_summary()}

@app.post("/api/upload-attachment")
async def upload_attachment(file: UploadFile = File(...)):
    """Upload an attachment file"""
    try:
        # Read file content
        file_content = await file.read()

        # Upload to agent
        result = await agent.upload_attachment(file_content, file.filename)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/attachments")
async def get_attachments():
    """Get list of all attachments"""
    return {"attachments": agent.get_attachments()}

@app.get("/api/attachment/{attachment_id}")
async def get_attachment(attachment_id: str):
    """Get attachment details and content"""
    result = await agent.get_attachment_content(attachment_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.delete("/api/attachment/{attachment_id}")
async def delete_attachment(attachment_id: str):
    """Delete an attachment"""
    result = await agent.delete_attachment(attachment_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return result

@app.get("/api/attachment/{attachment_id}/thumbnail")
async def get_attachment_thumbnail(attachment_id: str):
    """Get attachment thumbnail"""
    attachment = agent.attachment_manager.get_attachment(attachment_id)
    if not attachment or not attachment.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(attachment.thumbnail_path, media_type="image/jpeg")

@app.get("/api/conversation-stats")
async def get_conversation_stats():
    """Get conversation statistics"""
    return agent.get_conversation_stats()

@app.get("/api/conversation-summary")
async def get_conversation_summary():
    """Get conversation summary"""
    return await agent.summarize_conversation()

@app.post("/api/web-search")
async def web_search(request: WebSearchRequest):
    """Perform web search"""
    return await agent.web_search(
        request.query,
        request.num_results,
        request.provider,
        request.include_content
    )

@app.post("/api/scrape-url")
async def scrape_url(request: UrlScrapeRequest):
    """Scrape content from URL"""
    return await agent.scrape_url(request.url, request.use_cache)

@app.post("/api/search-and-summarize")
async def search_and_summarize(request: WebSearchRequest):
    """Search web and provide summary"""
    return await agent.search_and_summarize(
        request.query,
        request.num_results,
        request.provider
    )

@app.get("/api/web-search-providers")
async def get_web_search_providers():
    """Get available web search providers"""
    return {"providers": agent.get_web_search_providers()}

@app.get("/api/web-cache-stats")
async def get_web_cache_stats():
    """Get web scraping cache statistics"""
    return agent.get_web_cache_stats()

@app.post("/api/moonshot-web-search")
async def moonshot_web_search(request: WebSearchRequest):
    """Use Moonshot Kimi's web search"""
    return await agent.moonshot_web_search(request.query, request.num_results)

@app.post("/api/moonshot-analyze-url")
async def moonshot_analyze_url(request: UrlScrapeRequest):
    """Use Moonshot Kimi to analyze URL"""
    return await agent.moonshot_analyze_url(request.url)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG
    )
