#!/usr/bin/env python3
"""
Setup script for MCP AI Coding Agent
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, check=True):
    """Run a command and return the result"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return None

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("Error: Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"Python version: {version.major}.{version.minor}.{version.micro} ✓")
    return True

def create_virtual_environment():
    """Create a virtual environment"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("Virtual environment already exists")
        return True
    
    print("Creating virtual environment...")
    result = run_command(f"{sys.executable} -m venv venv")
    
    if result and result.returncode == 0:
        print("Virtual environment created successfully ✓")
        return True
    else:
        print("Failed to create virtual environment")
        return False

def get_pip_command():
    """Get the appropriate pip command for the current platform"""
    if platform.system() == "Windows":
        return "venv\\Scripts\\pip"
    else:
        return "venv/bin/pip"

def get_python_command():
    """Get the appropriate python command for the current platform"""
    if platform.system() == "Windows":
        return "venv\\Scripts\\python"
    else:
        return "venv/bin/python"

def install_dependencies():
    """Install Python dependencies"""
    print("Installing dependencies...")
    
    pip_cmd = get_pip_command()
    
    # Upgrade pip first
    result = run_command(f"{pip_cmd} install --upgrade pip")
    if not result or result.returncode != 0:
        print("Failed to upgrade pip")
        return False
    
    # Install requirements
    result = run_command(f"{pip_cmd} install -r requirements.txt")
    if not result or result.returncode != 0:
        print("Failed to install dependencies")
        return False
    
    print("Dependencies installed successfully ✓")
    return True

def setup_environment_file():
    """Set up environment configuration file"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print(".env file already exists")
        return True
    
    if env_example.exists():
        print("Creating .env file from template...")
        with open(env_example, 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print(".env file created ✓")
        print("Please edit .env file to add your API keys")
    else:
        print("Warning: .env.example not found")
    
    return True

def check_ollama():
    """Check if Ollama is installed and running"""
    print("Checking Ollama installation...")
    
    # Check if ollama command exists
    result = run_command("ollama --version", check=False)
    if not result or result.returncode != 0:
        print("Ollama not found. Please install Ollama for local models:")
        print("Visit: https://ollama.ai/")
        return False
    
    print("Ollama found ✓")
    
    # Check if Ollama is running
    result = run_command("ollama list", check=False)
    if not result or result.returncode != 0:
        print("Ollama is not running. Please start Ollama:")
        if platform.system() == "Windows":
            print("Run: ollama serve")
        else:
            print("Run: ollama serve")
        return False
    
    print("Ollama is running ✓")
    return True

def suggest_models():
    """Suggest models to download"""
    print("\nSuggested models to download with Ollama:")
    print("For coding tasks:")
    print("  ollama pull codellama:7b")
    print("  ollama pull qwen2.5-coder:7b")
    print("  ollama pull mistral:7b")
    print("\nFor general use:")
    print("  ollama pull llama3:8b")
    print("  ollama pull phi3:3.8b")
    print("\nNote: Larger models require more RAM but provide better performance")

def create_directories():
    """Create necessary directories"""
    directories = [
        ".mcp_backups",
        "static",
        "models",
        "core"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("Directories created ✓")

def main():
    """Main setup function"""
    print("=" * 50)
    print("MCP AI Coding Agent Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Create directories
    create_directories()
    
    # Create virtual environment
    if not create_virtual_environment():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Setup environment file
    setup_environment_file()
    
    # Check Ollama
    ollama_available = check_ollama()
    
    print("\n" + "=" * 50)
    print("Setup Complete!")
    print("=" * 50)
    
    print("\nNext steps:")
    print("1. Edit .env file to add your API keys (optional)")
    
    if not ollama_available:
        print("2. Install and start Ollama for local models")
        print("   Visit: https://ollama.ai/")
    else:
        suggest_models()
    
    print(f"\n3. Start the application:")
    if platform.system() == "Windows":
        print("   venv\\Scripts\\python app.py")
    else:
        print("   venv/bin/python app.py")
    
    print("\n4. Open your browser to: http://localhost:8000")
    
    print("\nFor more information, see README.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
