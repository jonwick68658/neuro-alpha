"""
Tool Executor
Safely executes user-generated tools with proper sandboxing
"""

import json
import sys
import io
import contextlib
from typing import Dict, Any, Optional
import traceback

class ToolExecutor:
    """Execute user-generated tools safely"""
    
    def __init__(self):
        self.available_imports = {
            'datetime', 'json', 'math', 'random', 'requests', 'urllib', 're', 
            'base64', 'hashlib', 'uuid', 'time', 'calendar'
        }
        
    def execute_tool(self, function_code: str, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool function with arguments
        
        Args:
            function_code: The Python function code
            function_name: Name of the function to call
            arguments: Arguments to pass to the function
            
        Returns:
            Dictionary with success status and result or error
        """
        # Initialize output capture
        captured_output = io.StringIO()
        
        try:
            # Create a safe execution environment
            safe_globals = {
                '__builtins__': {
                    'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
                    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
                    'min': min, 'max': max, 'sum': sum, 'abs': abs, 'round': round,
                    'range': range, 'enumerate': enumerate, 'zip': zip,
                    'print': print, 'type': type, 'isinstance': isinstance,
                    'ValueError': ValueError, 'TypeError': TypeError, 'KeyError': KeyError,
                    'Exception': Exception
                }
            }
            
            # Add allowed imports
            self._add_safe_imports(safe_globals)
            
            with contextlib.redirect_stdout(captured_output):
                # Execute the function code in safe environment
                exec(function_code, safe_globals)
                
                # Get the function from the executed code
                if function_name not in safe_globals:
                    return {
                        'success': False,
                        'error': f'Function {function_name} not found in code',
                        'output': captured_output.getvalue()
                    }
                
                function_obj = safe_globals[function_name]
                
                # Verify it's callable
                if not callable(function_obj):
                    return {
                        'success': False,
                        'error': f'{function_name} is not a callable function',
                        'output': captured_output.getvalue()
                    }
                
                # Execute the function with arguments
                result = function_obj(**arguments)
                
                return {
                    'success': True,
                    'result': result,
                    'output': captured_output.getvalue()
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'output': captured_output.getvalue()
            }
    
    def _add_safe_imports(self, safe_globals: Dict[str, Any]):
        """Add safe imports to execution environment"""
        try:
            # Import allowed modules
            import datetime
            import json
            import math
            import random
            import re
            import base64
            import hashlib
            import uuid
            import time
            import calendar
            
            safe_globals.update({
                'datetime': datetime,
                'json': json,
                'math': math,
                'random': random,
                're': re,
                'base64': base64,
                'hashlib': hashlib,
                'uuid': uuid,
                'time': time,
                'calendar': calendar
            })
            
            # Add requests with basic safety
            try:
                import requests
                safe_globals['requests'] = requests
            except ImportError:
                pass
                
        except Exception as e:
            print(f"Warning: Error adding safe imports: {e}")
    
    def validate_function_safety(self, function_code: str) -> Dict[str, Any]:
        """
        Validate that function code is safe to execute
        
        Args:
            function_code: The Python function code to validate
            
        Returns:
            Dictionary with validation status and any warnings
        """
        warnings = []
        
        # Check for dangerous operations
        dangerous_patterns = [
            'import os', 'import sys', 'import subprocess', 'import shutil',
            'open(', 'file(', 'exec(', 'eval(', 'compile(',
            '__import__', 'globals(', 'locals(', 'vars(',
            'delattr', 'setattr', 'getattr',
            'input(', 'raw_input(',
        ]
        
        for pattern in dangerous_patterns:
            if pattern in function_code:
                warnings.append(f"Potentially unsafe operation detected: {pattern}")
        
        # Check function complexity (basic limit)
        lines = function_code.count('\n')
        if lines > 50:
            warnings.append(f"Function is quite long ({lines} lines) - consider simplifying")
        
        return {
            'is_safe': len(warnings) == 0,
            'warnings': warnings
        }