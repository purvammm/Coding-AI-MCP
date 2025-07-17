# MCP AI Coding Agent

An AI coding agent that uses free, open-source AI models to help with coding tasks. This agent can:

- Use multiple free AI models (with dropdown selection)
- Run terminal commands (automatic and manual modes)
- Read, create, edit, and remove files
- Index and understand project files
- Assist with coding tasks and project development

## Features

- **Multiple AI Model Support**: Integrates with various free and open-source AI models
- **File Operations**: Can read, create, edit, and delete files in your project
- **Terminal Command Execution**: Run commands in automatic or manual mode
- **Project Indexing**: Scans and understands your project structure
- **Attachment Support**: Upload and process PDFs, images, documents, and other files
- **Smart Context Management**: Intelligent conversation history management for long threads
- **Content Extraction**: OCR for images, text extraction from PDFs and documents
- **Web Interface**: User-friendly interface with drag-and-drop file upload

## Supported AI Models

### Local Models (via Ollama)
- CodeLlama (7B, 13B, 34B)
- Qwen2.5-Coder (1.5B, 3B, 7B, 14B, 32B)
- Mistral (7B, 8x7B)
- Llama 3 (8B, 70B)
- Phi-3 (3.8B, 14B)
- DeepSeek Coder (6.7B, 33B)

### API-based Models
- Hugging Face Inference API (free tier)
- Groq API (free tier)
- Together AI (free tier)
- Replicate (limited free usage)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-ai.git
cd mcp-ai

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the application
python app.py
```

## Configuration

Create a `.env` file in the root directory with your API keys (optional):

```
HUGGINGFACE_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
TOGETHER_API_KEY=your_key_here
REPLICATE_API_KEY=your_key_here
```

## Usage

1. Start the application with `python app.py`
2. Open your browser at `http://localhost:8000`
3. Select an AI model from the dropdown
4. Enter your coding request or question
5. View and apply the suggested changes

## License

MIT
