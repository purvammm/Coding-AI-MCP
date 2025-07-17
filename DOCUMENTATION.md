# MCP AI Coding Agent Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Features](#features)
6. [AI Models](#ai-models)
7. [API Reference](#api-reference)
8. [Troubleshooting](#troubleshooting)
9. [Security Considerations](#security-considerations)
10. [Contributing](#contributing)

## Introduction

MCP AI Coding Agent is an AI-powered coding assistant that uses free, open-source AI models to help with coding tasks. It provides a web interface for interacting with AI models, executing terminal commands, and managing files in your project.

### Key Features

- **Multiple AI Model Support**: Use various free and open-source AI models
- **File Operations**: Read, create, edit, and delete files
- **Terminal Command Execution**: Run commands with safety checks
- **Project Indexing**: Understand your project structure and code
- **Web Interface**: User-friendly interface with model selection dropdown

## Installation

### Prerequisites

- Python 3.8 or higher
- Ollama (for local models) - [https://ollama.ai](https://ollama.ai)

### Windows Installation

1. Download or clone the repository
2. Run `install.bat`
3. Follow the on-screen instructions

### Linux/macOS Installation

1. Download or clone the repository
2. Make the install script executable: `chmod +x install.sh`
3. Run `./install.sh`
4. Follow the on-screen instructions

### Manual Installation

1. Create a virtual environment: `python -m venv venv`
2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/macOS: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and configure as needed
5. Start the application: `python run.py`

## Configuration

Configuration is managed through the `.env` file. Copy `.env.example` to `.env` and edit as needed.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | localhost |
| `PORT` | Server port | 8000 |
| `DEBUG` | Enable debug mode | true |
| `MAX_FILE_SIZE` | Maximum file size in bytes | 10485760 (10MB) |
| `BACKUP_DIR` | Directory for file backups | .mcp_backups |
| `TERMINAL_TIMEOUT` | Terminal command timeout in seconds | 30 |
| `AUTO_MODE` | Enable automatic command execution | false |

### API Keys (Optional)

For cloud-based models, you'll need to obtain API keys from the respective providers:

- **Groq API Key**: [https://console.groq.com/](https://console.groq.com/)
- **Hugging Face API Key**: [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
- **Together AI API Key**: [https://api.together.xyz/settings/api-keys](https://api.together.xyz/settings/api-keys)
- **Replicate API Key**: [https://replicate.com/account/api-tokens](https://replicate.com/account/api-tokens)

## Usage

### Starting the Application

1. Activate the virtual environment (if not already activated):
   - Windows: `venv\Scripts\activate`
   - Linux/macOS: `source venv/bin/activate`
2. Run the application: `python run.py`
3. Open your browser to: `http://localhost:8000`

### Using the Web Interface

1. **Select an AI Model**: Choose a model from the dropdown menu
2. **Chat with AI**: Enter your coding questions or requests in the chat input
3. **Execute Commands**: Run terminal commands in the terminal input
4. **Browse Files**: Use the file explorer to view and manage files
5. **Search Code**: Search for symbols in your codebase

## Features

### AI Chat

The chat interface allows you to interact with the selected AI model. You can:

- Ask coding questions
- Request code generation
- Get help with debugging
- Analyze code structure
- Get suggestions for improvements

### File Operations

The file explorer allows you to:

- Browse project files and directories
- View file contents
- Create new files
- Edit existing files
- Delete files (with backup)

### Terminal Commands

The terminal interface allows you to:

- Execute shell commands
- View command output in real-time
- Run commands with auto-approval (optional)
- View command history
- Kill running processes

### Project Indexing

The project indexer:

- Scans your project files
- Extracts code symbols (functions, classes, variables)
- Analyzes dependencies
- Provides search functionality
- Generates project statistics

## AI Models

### Local Models (via Ollama)

These models run locally on your machine using Ollama:

| Model | Size | Description |
|-------|------|-------------|
| CodeLlama | 7B, 13B, 34B | Meta's CodeLlama models specialized for code generation |
| Qwen2.5-Coder | 1.5B, 3B, 7B, 14B, 32B | Alibaba's Qwen2.5-Coder models for coding tasks |
| Mistral | 7B, 8x7B | Mistral's general-purpose models with good coding abilities |
| Llama 3 | 8B, 70B | Meta's latest Llama models |
| Phi-3 | 3.8B, 14B | Microsoft's Phi-3 models |
| DeepSeek Coder | 6.7B, 33B | DeepSeek's specialized coding models |

### API-based Models

These models are accessed through API providers:

| Provider | Models | API Key Required |
|----------|--------|------------------|
| Groq | Llama 3 70B, Mixtral 8x7B | Yes |
| Together AI | CodeLlama 34B, Llama 3 | Yes |
| Hugging Face | Qwen2.5-Coder, DeepSeek Coder | Yes |
| Replicate | Various models | Yes |
| Moonshot Kimi | v1 8K, v1 32K, v1 128K | Yes |

### Moonshot Kimi (Agentic AI)

Moonshot Kimi provides advanced agentic AI capabilities with built-in web search:

| Model | Context | Features |
|-------|---------|----------|
| moonshot-v1-8k | 8K tokens | Basic agentic capabilities |
| moonshot-v1-32k | 32K tokens | Extended context |
| moonshot-v1-128k | 128K tokens | Ultra-long context + web search |

### Installing Local Models

To install local models with Ollama:

```bash
# Install Ollama from https://ollama.ai

# Pull models
ollama pull codellama:7b
ollama pull qwen2.5-coder:7b
ollama pull mistral:7b
ollama pull llama3:8b
```

## API Reference

The MCP AI Coding Agent provides a REST API and WebSocket API for integration with other tools.

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/models` | GET | Get available AI models |
| `/api/current-model` | GET | Get current selected model |
| `/api/select-model` | POST | Select AI model |
| `/api/chat` | POST | Chat with AI (non-streaming) |
| `/api/file-operation` | POST | Execute file operation |
| `/api/terminal-command` | POST | Execute terminal command (non-streaming) |
| `/api/conversation-history` | GET | Get conversation history |
| `/api/clear-conversation` | POST | Clear conversation history |
| `/api/search-code` | POST | Search code symbols |
| `/api/project-summary` | GET | Get project summary |
| `/api/file-operations-log` | GET | Get file operations log |
| `/api/terminal-history` | GET | Get terminal command history |
| `/api/running-processes` | GET | Get running processes |
| `/api/kill-process/{pid}` | POST | Kill a running process |
| `/api/rebuild-index` | POST | Rebuild project index |
| `/api/web-search` | POST | Perform web search |
| `/api/scrape-url` | POST | Scrape content from URL |
| `/api/search-and-summarize` | POST | Search web and provide summary |
| `/api/web-search-providers` | GET | Get available search providers |
| `/api/web-cache-stats` | GET | Get web scraping cache stats |
| `/api/moonshot-web-search` | POST | Use Moonshot's web search |
| `/api/moonshot-analyze-url` | POST | Use Moonshot to analyze URL |

### WebSocket API

| Endpoint | Description |
|----------|-------------|
| `/ws/chat` | WebSocket for streaming chat |
| `/ws/terminal` | WebSocket for streaming terminal commands |

## Troubleshooting

### Common Issues

#### Ollama Not Found

If you see "Ollama not found" error:

1. Install Ollama from [https://ollama.ai](https://ollama.ai)
2. Start Ollama with `ollama serve`
3. Restart the application

#### API Key Issues

If you're having trouble with API-based models:

1. Check that you've added the correct API keys to your `.env` file
2. Verify that your API keys are valid and have not expired
3. Check if you've reached API rate limits

#### Model Not Loading

If a model fails to load:

1. For local models, check if Ollama is running
2. For API models, check your API key and internet connection
3. Check if the model is available from the provider

### Logs

Application logs can be found in the console output. If you need more detailed logs, set `DEBUG=true` in your `.env` file.

## Security Considerations

### File Operations

- File operations are restricted to the workspace directory
- Backups are created before modifying or deleting files
- File extensions are validated to prevent dangerous operations

### Terminal Commands

- Potentially dangerous commands require explicit approval
- Commands are validated before execution
- Command execution is limited to the workspace directory
- Timeout is enforced to prevent hanging commands

### API Keys

- API keys are stored locally in the `.env` file
- API keys are never exposed in the web interface
- HTTPS is recommended for production deployments

### Security Analysis Mode

For security researchers and developers who need to test the system's security mechanisms, a special Security Analysis Mode is available. This mode disables most security restrictions to allow for thorough testing and analysis.

**WARNING: Only use this mode in controlled, isolated environments for security research purposes.**

To enable Security Analysis Mode, set the following in your `.env` file:

```
SECURITY_ANALYSIS_MODE=true
```

You can also selectively disable specific security features:

```
ENABLE_COMMAND_VALIDATION=false
ENABLE_DANGEROUS_COMMAND_DETECTION=false
ENABLE_PATH_VALIDATION=false
ENABLE_FILE_EXTENSION_VALIDATION=false
```

When Security Analysis Mode is enabled:
- Command validation is disabled (allowing injection patterns)
- Dangerous command detection is bypassed
- Path validation is disabled (allowing access outside workspace)
- File extension validation is disabled
- Most safety prompts are bypassed

**Security Implications:**
- This mode can potentially allow destructive operations
- It may expose sensitive files on your system
- It could allow execution of malicious commands
- Use only for legitimate security research and testing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Fork the repository
2. Clone your fork
3. Create a virtual environment
4. Install dependencies with `pip install -r requirements.txt`
5. Make your changes
6. Test your changes
7. Submit a pull request

### Code Structure

- `app.py`: Main FastAPI application
- `config.py`: Configuration settings
- `core/`: Core functionality
  - `agent.py`: Main agent class
  - `file_manager.py`: File operations
  - `terminal_manager.py`: Terminal commands
  - `project_indexer.py`: Project indexing
- `models/`: AI model providers
  - `base.py`: Base model provider interface
  - `ollama.py`: Ollama provider
  - `groq.py`: Groq provider
  - `huggingface.py`: Hugging Face provider
  - `together.py`: Together AI provider
- `static/`: Web interface files
