import os
import shutil
import aiofiles
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json
import hashlib

from config import Config

@dataclass
class FileInfo:
    path: str
    name: str
    size: int
    modified: datetime
    is_directory: bool
    extension: Optional[str] = None
    content_preview: Optional[str] = None

@dataclass
class FileOperation:
    operation: str  # 'create', 'edit', 'delete', 'move', 'copy'
    path: str
    backup_path: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class FileManager:
    """Manages file operations with backup and safety features"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.backup_dir = self.workspace_path / Config.BACKUP_DIR
        self.backup_dir.mkdir(exist_ok=True)
        self.operation_log: List[FileOperation] = []
    
    async def read_file(self, file_path: str) -> str:
        """Read file content"""
        full_path = self._get_full_path(file_path)
        self._validate_path(full_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if full_path.stat().st_size > Config.MAX_FILE_SIZE:
            raise ValueError(f"File too large: {file_path}")
        
        try:
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except UnicodeDecodeError:
            # Try reading as binary and decode with error handling
            async with aiofiles.open(full_path, 'rb') as f:
                content = await f.read()
                return content.decode('utf-8', errors='replace')
    
    async def write_file(self, file_path: str, content: str, create_backup: bool = True) -> bool:
        """Write content to file with optional backup"""
        full_path = self._get_full_path(file_path)

        # Path validation (can be disabled for security analysis)
        if Config.ENABLE_PATH_VALIDATION and not Config.SECURITY_ANALYSIS_MODE:
            self._validate_path(full_path)

        # Extension validation (can be disabled for security analysis)
        if Config.ENABLE_FILE_EXTENSION_VALIDATION and not Config.SECURITY_ANALYSIS_MODE:
            self._validate_extension(full_path)
        
        # Create backup if file exists
        backup_path = None
        if create_backup and full_path.exists():
            backup_path = await self._create_backup(full_path)
        
        try:
            # Ensure parent directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            # Log operation
            operation = FileOperation(
                operation='edit' if backup_path else 'create',
                path=str(full_path),
                backup_path=backup_path
            )
            self.operation_log.append(operation)
            
            return True
        except Exception as e:
            # Restore backup if write failed
            if backup_path and Path(backup_path).exists():
                shutil.copy2(backup_path, full_path)
            raise Exception(f"Failed to write file {file_path}: {str(e)}")
    
    async def delete_file(self, file_path: str, create_backup: bool = True) -> bool:
        """Delete file with optional backup"""
        full_path = self._get_full_path(file_path)

        # Path validation (can be disabled for security analysis)
        if Config.ENABLE_PATH_VALIDATION and not Config.SECURITY_ANALYSIS_MODE:
            self._validate_path(full_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        backup_path = None
        if create_backup:
            backup_path = await self._create_backup(full_path)
        
        try:
            if full_path.is_file():
                full_path.unlink()
            elif full_path.is_dir():
                shutil.rmtree(full_path)
            
            # Log operation
            operation = FileOperation(
                operation='delete',
                path=str(full_path),
                backup_path=backup_path
            )
            self.operation_log.append(operation)
            
            return True
        except Exception as e:
            raise Exception(f"Failed to delete {file_path}: {str(e)}")
    
    async def list_files(self, directory_path: str = ".", include_hidden: bool = False) -> List[FileInfo]:
        """List files and directories"""
        full_path = self._get_full_path(directory_path)
        self._validate_path(full_path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        if not full_path.is_dir():
            raise ValueError(f"Path is not a directory: {directory_path}")
        
        files = []
        try:
            for item in full_path.iterdir():
                if not include_hidden and item.name.startswith('.'):
                    continue
                
                stat = item.stat()
                file_info = FileInfo(
                    path=str(item.relative_to(self.workspace_path)),
                    name=item.name,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    is_directory=item.is_dir(),
                    extension=item.suffix if item.is_file() else None
                )
                
                # Add content preview for small text files
                if (item.is_file() and 
                    item.suffix in Config.ALLOWED_EXTENSIONS and 
                    stat.st_size < 1024):  # 1KB preview limit
                    try:
                        with open(item, 'r', encoding='utf-8') as f:
                            preview = f.read(200)  # First 200 chars
                            file_info.content_preview = preview
                    except:
                        pass
                
                files.append(file_info)
        except Exception as e:
            raise Exception(f"Failed to list directory {directory_path}: {str(e)}")
        
        return sorted(files, key=lambda x: (not x.is_directory, x.name.lower()))
    
    async def move_file(self, source_path: str, dest_path: str) -> bool:
        """Move/rename file or directory"""
        source_full = self._get_full_path(source_path)
        dest_full = self._get_full_path(dest_path)
        
        self._validate_path(source_full)
        self._validate_path(dest_full)
        
        if not source_full.exists():
            raise FileNotFoundError(f"Source not found: {source_path}")
        
        if dest_full.exists():
            raise ValueError(f"Destination already exists: {dest_path}")
        
        try:
            # Ensure destination directory exists
            dest_full.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source_full), str(dest_full))
            
            # Log operation
            operation = FileOperation(
                operation='move',
                path=f"{source_path} -> {dest_path}"
            )
            self.operation_log.append(operation)
            
            return True
        except Exception as e:
            raise Exception(f"Failed to move {source_path} to {dest_path}: {str(e)}")
    
    async def copy_file(self, source_path: str, dest_path: str) -> bool:
        """Copy file or directory"""
        source_full = self._get_full_path(source_path)
        dest_full = self._get_full_path(dest_path)
        
        self._validate_path(source_full)
        self._validate_path(dest_full)
        
        if not source_full.exists():
            raise FileNotFoundError(f"Source not found: {source_path}")
        
        try:
            # Ensure destination directory exists
            dest_full.parent.mkdir(parents=True, exist_ok=True)
            
            if source_full.is_file():
                shutil.copy2(str(source_full), str(dest_full))
            else:
                shutil.copytree(str(source_full), str(dest_full))
            
            # Log operation
            operation = FileOperation(
                operation='copy',
                path=f"{source_path} -> {dest_path}"
            )
            self.operation_log.append(operation)
            
            return True
        except Exception as e:
            raise Exception(f"Failed to copy {source_path} to {dest_path}: {str(e)}")
    
    async def _create_backup(self, file_path: Path) -> str:
        """Create backup of file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
        backup_name = f"{file_path.name}_{timestamp}_{file_hash}"
        backup_path = self.backup_dir / backup_name
        
        try:
            if file_path.is_file():
                shutil.copy2(file_path, backup_path)
            else:
                shutil.copytree(file_path, backup_path)
            return str(backup_path)
        except Exception as e:
            raise Exception(f"Failed to create backup: {str(e)}")
    
    def _get_full_path(self, file_path: str) -> Path:
        """Get full path relative to workspace"""
        if os.path.isabs(file_path):
            full_path = Path(file_path)
        else:
            full_path = self.workspace_path / file_path
        return full_path.resolve()
    
    def _validate_path(self, full_path: Path):
        """Validate that path is within workspace (can be disabled for security analysis)"""
        if Config.SECURITY_ANALYSIS_MODE:
            return  # Skip validation in security analysis mode

        try:
            full_path.relative_to(self.workspace_path)
        except ValueError:
            raise ValueError(f"Path outside workspace: {full_path}")

    def _validate_extension(self, full_path: Path):
        """Validate file extension (can be disabled for security analysis)"""
        if Config.SECURITY_ANALYSIS_MODE:
            return  # Skip validation in security analysis mode

        if full_path.suffix and full_path.suffix not in Config.ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension not allowed: {full_path.suffix}")
    
    def get_operation_log(self) -> List[Dict]:
        """Get operation log as JSON-serializable format"""
        return [
            {
                'operation': op.operation,
                'path': op.path,
                'backup_path': op.backup_path,
                'timestamp': op.timestamp.isoformat()
            }
            for op in self.operation_log
        ]
