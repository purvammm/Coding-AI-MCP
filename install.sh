#!/bin/bash

# Linux/macOS installation script for MCP AI Coding Agent

echo "================================================"
echo "MCP AI Coding Agent - Linux/macOS Installation"
echo "================================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "Python found!"

# Make setup script executable
chmod +x setup.py

# Run the setup script
python3 setup.py

if [ $? -ne 0 ]; then
    echo "Setup failed!"
    exit 1
fi

echo ""
echo "================================================"
echo "Installation Complete!"
echo "================================================"
echo ""
echo "To start the application:"
echo "  1. Run: venv/bin/python run.py"
echo "  2. Open your browser to: http://localhost:8000"
echo ""
echo "For local AI models, install Ollama from: https://ollama.ai"
echo ""
