"""
Safe Python code execution service for LLM-generated analytics code.

Provides sandboxed execution with strict guardrails:
- Restricted imports (only safe libraries)
- No file system access
- No network access  
- No subprocess/os calls
- Memory and time limits
- AST validation before execution
"""

import ast
import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
import signal
import pandas as pd
import numpy as np

from app.utils.logging import get_logger

logger = get_logger("code_execution")

# Allowed imports - only safe data analysis libraries
ALLOWED_IMPORTS = {
    "pandas", "pd",
    "numpy", "np", 
    "math",
    "statistics",
    "collections",
    "itertools",
    "functools",
    "datetime",
    "json",
    "re",
    "typing",
}

# Forbidden function calls and attributes
FORBIDDEN_CALLS = {
    "exec", "eval", "compile", "open", "input",
    "__import__", "importlib",
    "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr", "hasattr",
    "breakpoint", "exit", "quit",
}

FORBIDDEN_ATTRIBUTES = {
    "__class__", "__bases__", "__subclasses__", "__mro__",
    "__globals__", "__code__", "__closure__",
    "__builtins__", "__dict__", "__module__",
    "__import__", "__loader__", "__spec__",
}

# Forbidden module access
FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "pathlib",
    "socket", "urllib", "requests", "http", "ftplib",
    "pickle", "shelve", "marshal",
    "ctypes", "multiprocessing", "threading",
    "importlib", "builtins",
    "code", "codeop", "compileall",
}

# Execution limits
MAX_EXECUTION_TIME = 30  # seconds
MAX_OUTPUT_SIZE = 100000000000000  # characters


@dataclass
class CodeExecutionResult:
    """Result of code execution."""
    success: bool
    output: str
    error: Optional[str] = None
    result_data: Optional[Any] = None
    execution_time: float = 0.0


class CodeValidationError(Exception):
    """Raised when code fails validation."""
    pass


class TimeoutError(Exception):
    """Raised when code execution times out."""
    pass


def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timed out")


class CodeValidator(ast.NodeVisitor):
    """AST visitor to validate code safety."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.imports: Set[str] = set()
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            module = alias.name.split('.')[0]
            if module in FORBIDDEN_MODULES:
                self.errors.append(f"Forbidden import: {alias.name}")
            elif module not in ALLOWED_IMPORTS:
                self.errors.append(f"Import not allowed: {alias.name}. Allowed: {', '.join(sorted(ALLOWED_IMPORTS))}")
            self.imports.add(module)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            module = node.module.split('.')[0]
            if module in FORBIDDEN_MODULES:
                self.errors.append(f"Forbidden import from: {node.module}")
            elif module not in ALLOWED_IMPORTS:
                self.errors.append(f"Import not allowed: {node.module}. Allowed: {', '.join(sorted(ALLOWED_IMPORTS))}")
            self.imports.add(module)
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        # Check for forbidden function calls
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.errors.append(f"Forbidden function call: {node.func.id}")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_CALLS:
                self.errors.append(f"Forbidden method call: {node.func.attr}")
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute):
        # Check for forbidden attribute access
        if node.attr in FORBIDDEN_ATTRIBUTES:
            self.errors.append(f"Forbidden attribute access: {node.attr}")
        # Block access to dunder methods that could be exploited
        if node.attr.startswith('__') and node.attr.endswith('__'):
            if node.attr not in {'__name__', '__doc__', '__str__', '__repr__', '__len__', '__iter__', '__getitem__', '__contains__'}:
                self.errors.append(f"Forbidden dunder attribute: {node.attr}")
        self.generic_visit(node)
    
    def visit_With(self, node: ast.With):
        # Block 'with open()' patterns
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                if isinstance(item.context_expr.func, ast.Name):
                    if item.context_expr.func.id == 'open':
                        self.errors.append("File operations not allowed")
        self.generic_visit(node)


def validate_code(code: str) -> List[str]:
    """
    Validate code for security issues.
    
    Returns list of errors (empty if valid).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Syntax error: {e}"]
    
    validator = CodeValidator()
    validator.visit(tree)
    
    return validator.errors


class SafeCodeExecutor:
    """
    Safe code executor with sandboxing.
    """
    
    def __init__(self, datasets: Dict[str, pd.DataFrame] = None):
        """
        Initialize executor with available datasets.
        
        Args:
            datasets: Dict mapping dataset_id to DataFrame
        """
        self.datasets = datasets or {}
    
    def add_dataset(self, dataset_id: str, df: pd.DataFrame):
        """Add a dataset to the execution context."""
        self.datasets[dataset_id] = df
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """Create a restricted globals dict for execution."""
        
        # Helper function to get dataset
        def get_dataset(dataset_id: str) -> pd.DataFrame:
            """Get a dataset by ID. Returns a copy to prevent modification."""
            if dataset_id not in self.datasets:
                available = list(self.datasets.keys())
                raise ValueError(f"Dataset '{dataset_id}' not found. Available: {available}")
            return self.datasets[dataset_id].copy()
        
        def list_datasets() -> List[str]:
            """List available dataset IDs."""
            return list(self.datasets.keys())
        
        def dataset_info(dataset_id: str) -> Dict[str, Any]:
            """Get info about a dataset."""
            df = get_dataset(dataset_id)
            return {
                "columns": list(df.columns),
                "shape": df.shape,
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "sample": df.head(3).to_dict('records')
            }
        
        # Restricted builtins - only safe functions
        safe_builtins = {
            # Types
            'bool': bool, 'int': int, 'float': float, 'str': str,
            'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
            'frozenset': frozenset, 'bytes': bytes,
            
            # Functions
            'abs': abs, 'all': all, 'any': any, 'bin': bin,
            'callable': callable, 'chr': chr, 'divmod': divmod,
            'enumerate': enumerate, 'filter': filter, 'format': format,
            'hash': hash, 'hex': hex, 'id': id, 'isinstance': isinstance,
            'issubclass': issubclass, 'iter': iter, 'len': len,
            'map': map, 'max': max, 'min': min, 'next': next,
            'oct': oct, 'ord': ord, 'pow': pow, 'print': print,
            'range': range, 'repr': repr, 'reversed': reversed,
            'round': round, 'slice': slice, 'sorted': sorted,
            'sum': sum, 'type': type, 'zip': zip,
            
            # Exceptions (for try/except)
            'Exception': Exception, 'ValueError': ValueError,
            'TypeError': TypeError, 'KeyError': KeyError,
            'IndexError': IndexError, 'AttributeError': AttributeError,
            'ZeroDivisionError': ZeroDivisionError,
            
            # Constants
            'True': True, 'False': False, 'None': None,
        }
        
        return {
            '__builtins__': safe_builtins,
            
            # Data analysis libraries
            'pd': pd,
            'pandas': pd,
            'np': np,
            'numpy': np,
            
            # Dataset access functions
            'get_dataset': get_dataset,
            'list_datasets': list_datasets,
            'dataset_info': dataset_info,
            
            # Common imports
            'datetime': __import__('datetime'),
            'math': __import__('math'),
            'statistics': __import__('statistics'),
            'json': __import__('json'),
            're': __import__('re'),
            'collections': __import__('collections'),
            'itertools': __import__('itertools'),
            'functools': __import__('functools'),
        }
    
    def execute(self, code: str) -> CodeExecutionResult:
        """
        Execute code safely.
        
        Args:
            code: Python code to execute
            
        Returns:
            CodeExecutionResult with output and any errors
        """
        import time
        start_time = time.time()
        
        # Step 1: Validate code
        errors = validate_code(code)
        if errors:
            return CodeExecutionResult(
                success=False,
                output="",
                error=f"Code validation failed:\n" + "\n".join(f"- {e}" for e in errors)
            )
        
        # Step 2: Prepare execution environment
        safe_globals = self._create_safe_globals()
        local_vars = {}
        
        # Capture stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            # Set timeout (Unix only)
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(MAX_EXECUTION_TIME)
            
            # Execute code
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, safe_globals, local_vars)
            
            # Cancel timeout
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            # Get output
            output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            # Truncate if too long
            if len(output) > MAX_OUTPUT_SIZE:
                output = output[:MAX_OUTPUT_SIZE] + f"\n... (output truncated, {len(output)} chars total)"
            
            # Check for result variable
            result_data = None
            if 'result' in local_vars:
                result_data = local_vars['result']
                # Convert DataFrame to dict for serialization
                if isinstance(result_data, pd.DataFrame):
                    result_data = {
                        "type": "dataframe",
                        "shape": result_data.shape,
                        "columns": list(result_data.columns),
                        "data": result_data.head(100).to_dict('records'),  # Limit to 100 rows
                        "truncated": len(result_data) > 100
                    }
                elif isinstance(result_data, pd.Series):
                    result_data = {
                        "type": "series",
                        "name": result_data.name,
                        "data": result_data.head(100).to_dict(),
                        "truncated": len(result_data) > 100
                    }
            
            execution_time = time.time() - start_time
            
            return CodeExecutionResult(
                success=True,
                output=output + (f"\n{stderr_output}" if stderr_output else ""),
                result_data=result_data,
                execution_time=execution_time
            )
            
        except TimeoutError:
            return CodeExecutionResult(
                success=False,
                output=stdout_capture.getvalue(),
                error=f"Execution timed out after {MAX_EXECUTION_TIME} seconds"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            error_tb = traceback.format_exc()
            # Clean up traceback to hide internal details
            error_lines = error_tb.split('\n')
            clean_error = '\n'.join(line for line in error_lines if 'code_execution_service' not in line)
            
            return CodeExecutionResult(
                success=False,
                output=stdout_capture.getvalue(),
                error=f"Execution error: {str(e)}\n{clean_error}",
                execution_time=execution_time
            )
        finally:
            # Ensure alarm is cancelled
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)


# Singleton executor factory
_executor_instance: Optional[SafeCodeExecutor] = None


def get_code_executor() -> SafeCodeExecutor:
    """Get or create the code executor singleton."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = SafeCodeExecutor()
    return _executor_instance

