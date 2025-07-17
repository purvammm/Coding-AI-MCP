import os
import ast
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import re

from config import Config

@dataclass
class CodeSymbol:
    name: str
    type: str  # 'function', 'class', 'variable', 'import'
    file_path: str
    line_number: int
    docstring: Optional[str] = None
    parameters: Optional[List[str]] = None
    return_type: Optional[str] = None
    parent: Optional[str] = None  # For methods in classes

@dataclass
class FileIndex:
    path: str
    language: str
    size: int
    lines: int
    last_modified: datetime
    hash: str
    symbols: List[CodeSymbol]
    imports: List[str]
    dependencies: List[str]
    summary: Optional[str] = None

@dataclass
class ProjectIndex:
    root_path: str
    total_files: int
    total_lines: int
    languages: Dict[str, int]  # language -> file count
    files: Dict[str, FileIndex]  # file_path -> FileIndex
    symbols: Dict[str, List[CodeSymbol]]  # symbol_name -> [CodeSymbol]
    dependencies: Dict[str, Set[str]]  # file -> dependencies
    last_updated: datetime

class ProjectIndexer:
    """Indexes project files for context-aware code understanding"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.index_cache_path = self.workspace_path / ".mcp_index.json"
        self.current_index: Optional[ProjectIndex] = None
        
        # Language patterns
        self.language_patterns = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala'
        }
    
    async def build_index(self, force_rebuild: bool = False) -> ProjectIndex:
        """Build or update the project index"""
        
        # Check if we can use cached index
        if not force_rebuild and self.index_cache_path.exists():
            try:
                cached_index = await self._load_cached_index()
                if cached_index and await self._is_index_current(cached_index):
                    self.current_index = cached_index
                    return cached_index
            except Exception:
                pass  # Fall back to rebuilding
        
        print("Building project index...")
        
        files: Dict[str, FileIndex] = {}
        symbols: Dict[str, List[CodeSymbol]] = {}
        dependencies: Dict[str, Set[str]] = {}
        languages: Dict[str, int] = {}
        total_lines = 0
        
        # Scan all files
        for file_path in self._get_source_files():
            try:
                file_index = await self._index_file(file_path)
                if file_index:
                    files[str(file_path.relative_to(self.workspace_path))] = file_index
                    
                    # Update language counts
                    lang = file_index.language
                    languages[lang] = languages.get(lang, 0) + 1
                    total_lines += file_index.lines
                    
                    # Index symbols
                    for symbol in file_index.symbols:
                        if symbol.name not in symbols:
                            symbols[symbol.name] = []
                        symbols[symbol.name].append(symbol)
                    
                    # Track dependencies
                    if file_index.dependencies:
                        dependencies[file_index.path] = set(file_index.dependencies)
                        
            except Exception as e:
                print(f"Error indexing {file_path}: {e}")
                continue
        
        # Create project index
        project_index = ProjectIndex(
            root_path=str(self.workspace_path),
            total_files=len(files),
            total_lines=total_lines,
            languages=languages,
            files=files,
            symbols=symbols,
            dependencies=dependencies,
            last_updated=datetime.now()
        )
        
        # Cache the index
        await self._save_index_cache(project_index)
        self.current_index = project_index
        
        print(f"Index built: {len(files)} files, {total_lines} lines, {len(symbols)} symbols")
        return project_index
    
    async def _index_file(self, file_path: Path) -> Optional[FileIndex]:
        """Index a single file"""
        try:
            # Get file stats
            stat = file_path.stat()
            if stat.st_size > Config.MAX_FILE_SIZE:
                return None
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Calculate hash
            file_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Determine language
            language = self.language_patterns.get(file_path.suffix, 'text')
            
            # Count lines
            lines = len(content.splitlines())
            
            # Extract symbols and dependencies
            symbols = []
            imports = []
            dependencies = []
            
            if language == 'python':
                symbols, imports, dependencies = self._parse_python_file(content, str(file_path))
            elif language in ['javascript', 'typescript']:
                symbols, imports, dependencies = self._parse_js_file(content, str(file_path))
            
            return FileIndex(
                path=str(file_path.relative_to(self.workspace_path)),
                language=language,
                size=stat.st_size,
                lines=lines,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                hash=file_hash,
                symbols=symbols,
                imports=imports,
                dependencies=dependencies
            )
            
        except Exception as e:
            print(f"Error indexing file {file_path}: {e}")
            return None
    
    def _parse_python_file(self, content: str, file_path: str) -> Tuple[List[CodeSymbol], List[str], List[str]]:
        """Parse Python file for symbols and dependencies"""
        symbols = []
        imports = []
        dependencies = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Function definition
                    params = [arg.arg for arg in node.args.args]
                    docstring = ast.get_docstring(node)
                    
                    symbol = CodeSymbol(
                        name=node.name,
                        type='function',
                        file_path=file_path,
                        line_number=node.lineno,
                        docstring=docstring,
                        parameters=params
                    )
                    symbols.append(symbol)
                
                elif isinstance(node, ast.ClassDef):
                    # Class definition
                    docstring = ast.get_docstring(node)
                    
                    symbol = CodeSymbol(
                        name=node.name,
                        type='class',
                        file_path=file_path,
                        line_number=node.lineno,
                        docstring=docstring
                    )
                    symbols.append(symbol)
                    
                    # Index methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            params = [arg.arg for arg in item.args.args]
                            method_docstring = ast.get_docstring(item)
                            
                            method_symbol = CodeSymbol(
                                name=item.name,
                                type='method',
                                file_path=file_path,
                                line_number=item.lineno,
                                docstring=method_docstring,
                                parameters=params,
                                parent=node.name
                            )
                            symbols.append(method_symbol)
                
                elif isinstance(node, ast.Import):
                    # Import statement
                    for alias in node.names:
                        imports.append(alias.name)
                        dependencies.append(alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    # From import statement
                    if node.module:
                        imports.append(node.module)
                        dependencies.append(node.module)
                        
                        for alias in node.names:
                            imports.append(f"{node.module}.{alias.name}")
                
                elif isinstance(node, ast.Assign):
                    # Variable assignment (top-level only)
                    if hasattr(node, 'lineno') and node.lineno < 100:  # Rough heuristic for top-level
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                symbol = CodeSymbol(
                                    name=target.id,
                                    type='variable',
                                    file_path=file_path,
                                    line_number=node.lineno
                                )
                                symbols.append(symbol)
        
        except SyntaxError:
            pass  # Skip files with syntax errors
        
        return symbols, imports, dependencies
    
    def _parse_js_file(self, content: str, file_path: str) -> Tuple[List[CodeSymbol], List[str], List[str]]:
        """Parse JavaScript/TypeScript file for symbols and dependencies"""
        symbols = []
        imports = []
        dependencies = []
        
        lines = content.splitlines()
        
        # Simple regex-based parsing (for a full implementation, use a proper parser)
        function_pattern = r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:function|\([^)]*\)\s*=>))'
        class_pattern = r'class\s+(\w+)'
        import_pattern = r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]'
        require_pattern = r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        
        for i, line in enumerate(lines, 1):
            # Functions
            func_match = re.search(function_pattern, line)
            if func_match:
                name = func_match.group(1) or func_match.group(2)
                if name:
                    symbol = CodeSymbol(
                        name=name,
                        type='function',
                        file_path=file_path,
                        line_number=i
                    )
                    symbols.append(symbol)
            
            # Classes
            class_match = re.search(class_pattern, line)
            if class_match:
                symbol = CodeSymbol(
                    name=class_match.group(1),
                    type='class',
                    file_path=file_path,
                    line_number=i
                )
                symbols.append(symbol)
            
            # Imports
            import_match = re.search(import_pattern, line)
            if import_match:
                module = import_match.group(1)
                imports.append(module)
                dependencies.append(module)
            
            require_match = re.search(require_pattern, line)
            if require_match:
                module = require_match.group(1)
                imports.append(module)
                dependencies.append(module)
        
        return symbols, imports, dependencies
    
    def _get_source_files(self) -> List[Path]:
        """Get all source files in the project"""
        source_files = []
        
        for root, dirs, files in os.walk(self.workspace_path):
            # Skip hidden directories and common build/cache directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                'node_modules', '__pycache__', 'build', 'dist', 'target', 'bin', 'obj'
            }]
            
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix in self.language_patterns:
                    source_files.append(file_path)
        
        return source_files
    
    async def _load_cached_index(self) -> Optional[ProjectIndex]:
        """Load cached index from disk"""
        try:
            with open(self.index_cache_path, 'r') as f:
                data = json.load(f)
            
            # Convert back to ProjectIndex
            # This is a simplified version - in practice you'd need proper deserialization
            return None  # For now, always rebuild
        except:
            return None
    
    async def _save_index_cache(self, index: ProjectIndex):
        """Save index to cache file"""
        try:
            # Convert to JSON-serializable format
            data = asdict(index)
            # Convert datetime objects to strings
            data['last_updated'] = index.last_updated.isoformat()
            
            with open(self.index_cache_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save index cache: {e}")
    
    async def _is_index_current(self, index: ProjectIndex) -> bool:
        """Check if cached index is still current"""
        # Simple check - in practice you'd check file modification times
        return False  # For now, always rebuild
    
    def search_symbols(self, query: str, symbol_type: Optional[str] = None) -> List[CodeSymbol]:
        """Search for symbols by name"""
        if not self.current_index:
            return []
        
        results = []
        query_lower = query.lower()
        
        for name, symbol_list in self.current_index.symbols.items():
            if query_lower in name.lower():
                for symbol in symbol_list:
                    if symbol_type is None or symbol.type == symbol_type:
                        results.append(symbol)
        
        return results
    
    def get_file_context(self, file_path: str) -> Optional[FileIndex]:
        """Get context for a specific file"""
        if not self.current_index:
            return None
        
        return self.current_index.files.get(file_path)
    
    def get_project_summary(self) -> Dict[str, Any]:
        """Get project summary statistics"""
        if not self.current_index:
            return {}
        
        return {
            'total_files': self.current_index.total_files,
            'total_lines': self.current_index.total_lines,
            'languages': self.current_index.languages,
            'symbol_count': len(self.current_index.symbols),
            'last_updated': self.current_index.last_updated.isoformat()
        }
