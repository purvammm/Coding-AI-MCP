#!/usr/bin/env python3
"""
Simple runner script for MCP AI Coding Agent
"""

import os
import sys
import asyncio
import uvicorn
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config

def main():
    """Main entry point"""
    print("Starting MCP AI Coding Agent...")
    print(f"Server will be available at: http://{Config.HOST}:{Config.PORT}")
    print("Press Ctrl+C to stop the server")
    
    # Run the FastAPI application
    uvicorn.run(
        "app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info" if Config.DEBUG else "warning"
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
