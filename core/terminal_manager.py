import asyncio
import subprocess
import os
import platform
import shlex
from datetime import datetime
from typing import List, Dict, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
import psutil

from config import Config

@dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    timestamp: datetime

@dataclass
class RunningProcess:
    pid: int
    command: str
    process: asyncio.subprocess.Process
    start_time: datetime

class TerminalManager:
    """Manages terminal command execution with safety features"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.command_history: List[CommandResult] = []
        self.running_processes: Dict[int, RunningProcess] = {}
        self.auto_mode = False
        
    async def execute_command(
        self,
        command: str,
        auto_approve: bool = False,
        timeout: int = None,
        capture_output: bool = True
    ) -> CommandResult:
        """Execute a command with configurable safety checks"""

        if timeout is None:
            timeout = Config.TERMINAL_TIMEOUT

        # Safety checks (can be disabled for security analysis)
        if Config.ENABLE_DANGEROUS_COMMAND_DETECTION and not auto_approve and not self.auto_mode and not Config.SECURITY_ANALYSIS_MODE:
            if self._is_dangerous_command(command):
                raise ValueError(f"Dangerous command requires manual approval: {command}")

        # Validate command (can be disabled for security analysis)
        if Config.ENABLE_COMMAND_VALIDATION and not Config.SECURITY_ANALYSIS_MODE:
            self._validate_command(command)
        
        start_time = datetime.now()
        
        try:
            # Prepare command for execution
            if platform.system() == "Windows":
                shell_command = ["cmd", "/c", command]
            else:
                shell_command = ["/bin/bash", "-c", command]
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *shell_command,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                cwd=str(self.workspace_path)
            )
            
            # Store running process
            running_proc = RunningProcess(
                pid=process.pid,
                command=command,
                process=process,
                start_time=start_time
            )
            self.running_processes[process.pid] = running_proc
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Command timed out after {timeout} seconds: {command}")
            finally:
                # Remove from running processes
                if process.pid in self.running_processes:
                    del self.running_processes[process.pid]
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = CommandResult(
                command=command,
                exit_code=process.returncode,
                stdout=stdout.decode('utf-8', errors='replace') if stdout else "",
                stderr=stderr.decode('utf-8', errors='replace') if stderr else "",
                execution_time=execution_time,
                timestamp=start_time
            )
            
            # Add to history
            self.command_history.append(result)
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            error_result = CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                timestamp=start_time
            )
            
            self.command_history.append(error_result)
            raise Exception(f"Failed to execute command '{command}': {str(e)}")
    
    async def execute_command_stream(
        self,
        command: str,
        auto_approve: bool = False,
        timeout: int = None
    ) -> AsyncGenerator[str, None]:
        """Execute command and stream output in real-time"""

        if timeout is None:
            timeout = Config.TERMINAL_TIMEOUT

        # Safety checks (can be disabled for security analysis)
        if Config.ENABLE_DANGEROUS_COMMAND_DETECTION and not auto_approve and not self.auto_mode and not Config.SECURITY_ANALYSIS_MODE:
            if self._is_dangerous_command(command):
                raise ValueError(f"Dangerous command requires manual approval: {command}")

        if Config.ENABLE_COMMAND_VALIDATION and not Config.SECURITY_ANALYSIS_MODE:
            self._validate_command(command)
        
        start_time = datetime.now()
        
        try:
            # Prepare command for execution
            if platform.system() == "Windows":
                shell_command = ["cmd", "/c", command]
            else:
                shell_command = ["/bin/bash", "-c", command]
            
            process = await asyncio.create_subprocess_exec(
                *shell_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout
                cwd=str(self.workspace_path)
            )
            
            # Store running process
            running_proc = RunningProcess(
                pid=process.pid,
                command=command,
                process=process,
                start_time=start_time
            )
            self.running_processes[process.pid] = running_proc
            
            output_lines = []
            
            try:
                # Stream output
                while True:
                    try:
                        line = await asyncio.wait_for(
                            process.stdout.readline(),
                            timeout=1.0
                        )
                        if not line:
                            break
                        
                        line_str = line.decode('utf-8', errors='replace').rstrip()
                        output_lines.append(line_str)
                        yield line_str
                        
                    except asyncio.TimeoutError:
                        # Check if process is still running
                        if process.returncode is not None:
                            break
                        continue
                
                await process.wait()
                
            except Exception as e:
                process.kill()
                await process.wait()
                raise e
            finally:
                # Remove from running processes
                if process.pid in self.running_processes:
                    del self.running_processes[process.pid]
            
            # Log the command result
            execution_time = (datetime.now() - start_time).total_seconds()
            result = CommandResult(
                command=command,
                exit_code=process.returncode,
                stdout="\n".join(output_lines),
                stderr="",
                execution_time=execution_time,
                timestamp=start_time
            )
            self.command_history.append(result)
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_result = CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                timestamp=start_time
            )
            self.command_history.append(error_result)
            raise Exception(f"Failed to execute command '{command}': {str(e)}")
    
    async def kill_process(self, pid: int) -> bool:
        """Kill a running process"""
        if pid in self.running_processes:
            try:
                process = self.running_processes[pid].process
                process.kill()
                await process.wait()
                del self.running_processes[pid]
                return True
            except Exception:
                return False
        
        # Try to kill system process
        try:
            proc = psutil.Process(pid)
            proc.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def get_running_processes(self) -> List[Dict]:
        """Get list of running processes"""
        return [
            {
                'pid': proc.pid,
                'command': proc.command,
                'start_time': proc.start_time.isoformat(),
                'duration': (datetime.now() - proc.start_time).total_seconds()
            }
            for proc in self.running_processes.values()
        ]
    
    def get_command_history(self, limit: int = 50) -> List[Dict]:
        """Get command history"""
        history = self.command_history[-limit:] if limit else self.command_history
        return [
            {
                'command': result.command,
                'exit_code': result.exit_code,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': result.execution_time,
                'timestamp': result.timestamp.isoformat()
            }
            for result in history
        ]
    
    def set_auto_mode(self, enabled: bool):
        """Enable/disable automatic command execution"""
        self.auto_mode = enabled
    
    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command is potentially dangerous"""
        command_lower = command.lower().strip()
        
        # Check for dangerous commands
        for dangerous_cmd in Config.DANGEROUS_COMMANDS:
            if command_lower.startswith(dangerous_cmd.lower()):
                return True
        
        # Check for file system operations outside workspace
        if any(pattern in command_lower for pattern in ['../', '../', '..\\', '..\\']):
            return True
        
        # Check for network operations
        if any(pattern in command_lower for pattern in ['curl', 'wget', 'ssh', 'scp', 'rsync']):
            return True
        
        return False
    
    def _validate_command(self, command: str):
        """Validate command before execution (can be disabled for security analysis)"""
        if not command or not command.strip():
            raise ValueError("Empty command")

        # In security analysis mode, allow more flexibility
        if Config.SECURITY_ANALYSIS_MODE:
            return

        if len(command) > 1000:
            raise ValueError("Command too long")

        # Check for command injection patterns (can be disabled)
        if Config.ENABLE_COMMAND_VALIDATION:
            suspicious_patterns = [';', '&&', '||', '|', '>', '>>', '<', '`', '$()']
            if any(pattern in command for pattern in suspicious_patterns):
                # Allow some safe patterns
                safe_patterns = ['pip install', 'npm install', 'git', 'python -m']
                if not any(safe in command.lower() for safe in safe_patterns):
                    raise ValueError("Command contains potentially unsafe patterns")
    
    async def suggest_commands(self, task_description: str) -> List[str]:
        """Suggest commands based on task description"""
        # This is a simple implementation - in a real system you'd use AI
        suggestions = []
        
        task_lower = task_description.lower()
        
        if 'install' in task_lower:
            if 'python' in task_lower or 'pip' in task_lower:
                suggestions.append("pip install <package_name>")
            if 'node' in task_lower or 'npm' in task_lower:
                suggestions.append("npm install <package_name>")
        
        if 'test' in task_lower:
            suggestions.extend([
                "python -m pytest",
                "npm test",
                "python -m unittest discover"
            ])
        
        if 'build' in task_lower:
            suggestions.extend([
                "python setup.py build",
                "npm run build",
                "make"
            ])
        
        if 'git' in task_lower:
            suggestions.extend([
                "git status",
                "git add .",
                "git commit -m 'message'",
                "git push"
            ])
        
        return suggestions
