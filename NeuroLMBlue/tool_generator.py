"""
Tool Generator Service
Creates custom tools based on user requests using Mistral-Small-3.2
"""

import json
import re
import ast
from typing import Dict, Optional, List
import requests
import os
from datetime import datetime

class ToolGenerator:
    """Generate custom tools using Mistral-Small-3.2 for function calling optimization"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "mistralai/devstral-small"
        
    def generate_tool(self, user_request: str, user_id: str) -> Optional[Dict]:
        """
        Generate a custom tool based on user request
        
        Args:
            user_request: User's description of what tool they need
            user_id: User ID for tool ownership
            
        Returns:
            Dictionary with tool_name, function_code, schema, description
        """
        try:
            # Generate tool using Mistral-Small-3.2
            tool_spec = self._request_tool_generation(user_request)
            
            if not tool_spec:
                return None
                
            # Validate the generated tool
            if not self._validate_tool(tool_spec):
                print(f"Generated tool failed validation: {tool_spec}")
                return None
                
            return {
                'tool_name': tool_spec['name'],
                'function_code': tool_spec['function_code'],
                'schema': tool_spec['schema'],
                'description': tool_spec['description'],
                'user_id': user_id,
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error generating tool: {e}")
            return None
    
    def _request_tool_generation(self, user_request: str) -> Optional[Dict]:
        """Request tool generation from Mistral-Small-3.2"""
        
        prompt = f"""Generate a Python function and OpenAI tool schema for this request: {user_request}

You must respond with valid JSON in this exact format:
{{
    "name": "function_name",
    "description": "What this tool does",
    "function_code": "def function_name(param1: str) -> str:\\n    # Implementation\\n    return result",
    "schema": {{
        "type": "function",
        "function": {{
            "name": "function_name",
            "description": "What this tool does",
            "parameters": {{
                "type": "object",
                "properties": {{
                    "param1": {{
                        "type": "string",
                        "description": "Parameter description"
                    }}
                }},
                "required": ["param1"],
                "additionalProperties": false
            }},
            "strict": true
        }}
    }}
}}

Requirements:
- Function must be simple and safe
- No file system access or dangerous operations
- CRITICAL: DO NOT use any import statements - function must work with built-in Python only
- For math operations, define constants directly (e.g., pi = 3.14159265359)
- Available built-ins: len, str, int, float, bool, list, dict, tuple, set, min, max, sum, abs, round, range, enumerate, zip
- Function name must be valid Python identifier
- Return meaningful results
- Keep it under 20 lines of code

Example for "calculate circle area":
{{
    "name": "calculate_circle_area",
    "description": "Calculate the area of a circle given radius",
    "function_code": "def calculate_circle_area(radius: float) -> float:\\n    pi = 3.14159265359\\n    return pi * (radius ** 2)",
    "schema": {{
        "type": "function",
        "function": {{
            "name": "calculate_circle_area",
            "description": "Calculate the area of a circle given radius",
            "parameters": {{
                "type": "object",
                "properties": {{
                    "radius": {{
                        "type": "number",
                        "description": "The radius of the circle"
                    }}
                }},
                "required": ["radius"],
                "additionalProperties": false
            }},
            "strict": true
        }}
    }}
}}

Generate tool for: {user_request}"""

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                },
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"API request failed: {response.status_code}")
                return None
                
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Extract JSON from response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                print(f"No JSON found in response: {content}")
                return None
                
            json_content = content[json_start:json_end]
            return json.loads(json_content)
            
        except Exception as e:
            print(f"Error requesting tool generation: {e}")
            return None
    
    def _validate_tool(self, tool_spec: Dict) -> bool:
        """Validate generated tool specification"""
        try:
            # Check required fields
            required_fields = ['name', 'description', 'function_code', 'schema']
            for field in required_fields:
                if field not in tool_spec:
                    print(f"Missing required field: {field}")
                    return False
            
            # Validate function name
            name = tool_spec['name']
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
                print(f"Invalid function name: {name}")
                return False
            
            # Validate Python syntax
            try:
                ast.parse(tool_spec['function_code'])
            except SyntaxError as e:
                print(f"Invalid Python syntax: {e}")
                return False
            
            # Validate schema structure
            schema = tool_spec['schema']
            if not isinstance(schema, dict) or 'function' not in schema:
                print("Invalid schema structure")
                return False
                
            func_schema = schema['function']
            if 'name' not in func_schema or 'parameters' not in func_schema:
                print("Invalid function schema")
                return False
            
            # Check name consistency
            if func_schema['name'] != name:
                print(f"Name mismatch: {name} vs {func_schema['name']}")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error validating tool: {e}")
            return False