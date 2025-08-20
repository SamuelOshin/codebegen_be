# Qwen generator implementation
"""
Qwen2.5-Coder model wrapper using Hugging Face Inference API.
Handles prompt formatting and code generation via HF Inference.
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional

try:
    from huggingface_hub import InferenceClient
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("Warning: huggingface_hub not available. Code generation will be limited.")

from app.core.config import settings

class QwenGenerator:
    def __init__(self, model_path: str = "Qwen/Qwen3-Coder-480B-A35B-Instruct"):
        self.model_path = model_path
        self.client = None
        
        # Initialize HF Inference client
        if HF_AVAILABLE:
            try:
                # Try to get HF token from environment
                hf_token = os.environ.get("HF_TOKEN") or getattr(settings, "HF_TOKEN", None)
                
                self.client = InferenceClient(
                    model=self.model_path,
                    token=hf_token
                )
                print(f"Qwen Generator initialized with model: {self.model_path}")
            except Exception as e:
                print(f"Warning: Failed to initialize HF Inference Client: {e}")
                self.client = None

    async def load(self):
        """Initialize the inference client (already done in __init__)"""
        if not HF_AVAILABLE:
            print("Warning: Cannot initialize - huggingface_hub not available")
            return
            
        if self.client is None:
            print("Warning: HF Inference Client not available - check HF_TOKEN")
            return
            
        print("Qwen Generator ready for inference")

    async def generate_project(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate complete FastAPI project from prompt and schema"""
        
        if not HF_AVAILABLE or not self.client:
            return self._generate_fallback_project(prompt, schema, context)
        
        formatted_prompt = self._format_generation_prompt(prompt, schema, context)
        
        try:
            # Use HF Inference API for generation
            output = await self._generate_with_hf(formatted_prompt)
            
            # Parse output to extract files
            files = self._parse_generated_output(output)
            return files
            
        except Exception as e:
            print(f"Error during HF generation: {e}")
            return self._generate_fallback_project(prompt, schema, context)

    async def _generate_with_hf(self, prompt: str) -> str:
        """Generate using Hugging Face Inference API"""
        try:
            # Use chat completion with Qwen
            messages = [
                {
                    "role": "system", 
                    "content": "You are Codebegen, an AI backend engineer that builds production-ready FastAPI backends from natural language requests."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Generate response
            response = self.client.chat_completion(
                messages=messages,
                max_tokens=8192,
                temperature=0.1,
                stream=False
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"HF Inference error: {e}")
            raise

    def _format_generation_prompt(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Format prompt for Qwen model"""
        
        user_prompt = f"""### API Description:
{prompt}

### Extracted Schema:
{json.dumps(schema, indent=2)}

### Technical Context:
Domain: {context.get('domain', 'general')}
Tech Stack: {context.get('tech_stack', 'fastapi_postgres')}
Constraints: {', '.join(context.get('constraints', []))}

### Requirements:
- Follow PEP8 and use `black` formatting.
- Use the requested tech stack exactly.
- Generate ALL required files for a working project.
- Include Dockerfile and docker-compose.yml when requested.
- Ensure code runs without syntax errors.
- Never invent package names.
- Always separate concerns into models, schemas, routers, services, and repositories.
- Include basic tests and README.md.

### Output Format:
Return JSON with:
{{
  "files": {{ "path/to/file.py": "<full code>", ... }}
}}"""

        return user_prompt

    def _parse_generated_output(self, output: str) -> Dict[str, str]:
        """Parse model output to extract file dictionary with robust error handling"""
        try:
            # Remove markdown code block markers
            if "```json" in output:
                # Extract content between ```json and ```
                start_marker = "```json"
                end_marker = "```"
                start_idx = output.find(start_marker) + len(start_marker)
                end_idx = output.rfind(end_marker)  # Use rfind to get the last ```
                if end_idx != -1 and end_idx > start_idx:
                    json_str = output[start_idx:end_idx].strip()
                else:
                    json_str = output[start_idx:].strip()
            else:
                # Find JSON in the output
                start_idx = output.find('{"files":')
                if start_idx == -1:
                    start_idx = output.find('{')
                
                json_str = output[start_idx:]
            
            # Clean up the JSON string
            json_str = json_str.strip()
            
            # Remove any trailing content after the JSON object ends
            brace_count = 0
            json_end = 0
            for i, char in enumerate(json_str):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            
            if json_end > 0:
                json_str = json_str[:json_end]
            
            # Parse JSON
            result = json.loads(json_str)
            return result.get("files", {})
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            print(f"Attempting to parse: {json_str[:200] if 'json_str' in locals() else output[:200]}...")
            
            # Try to fix unterminated strings in JSON
            try:
                if 'json_str' in locals():
                    # Fix unterminated strings by finding common patterns
                    fixed_json = self._fix_json_strings(json_str)
                    result = json.loads(fixed_json)
                    return result.get("files", {})
            except Exception:
                pass
            
            # Try to fix the JSON by manual extraction
            try:
                return self._manual_file_extraction(output)
            except Exception as manual_error:
                print(f"Manual extraction also failed: {manual_error}")
                return self._create_fallback_files(output)

    def _fix_json_strings(self, json_str: str) -> str:
        """Attempt to fix unterminated strings in JSON"""
        import re
        
        # Fix common patterns of unterminated strings
        # Pattern: "key": "value with no closing quote
        pattern = r'"([^"]+)": "([^"]*?)(?=\n\s*["},]|$)'
        
        def fix_match(match):
            key = match.group(1)
            value = match.group(2)
            # Add closing quote if missing
            if not value.endswith('"'):
                return f'"{key}": "{value}"'
            return match.group(0)
        
        fixed = re.sub(pattern, fix_match, json_str, flags=re.MULTILINE | re.DOTALL)
        
        # Ensure proper JSON closure
        if not fixed.rstrip().endswith('}'):
            # Count braces to determine proper closure
            open_braces = fixed.count('{')
            close_braces = fixed.count('}')
            missing_braces = open_braces - close_braces
            fixed += '}' * missing_braces
        
        return fixed

    def _create_fallback_files(self, output: str) -> Dict[str, str]:
        """Create basic files when parsing completely fails"""
        return {
            "main.py": '''"""FastAPI application generated by Qwen."""

from fastapi import FastAPI

app = FastAPI(title="Generated API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
''',
            "requirements.txt": '''fastapi>=0.68.0
uvicorn>=0.15.0
pydantic>=1.8.0
''',
            "README.md": f'''# Generated Project

This project was generated but had parsing issues.

## Original Output (truncated):
```
{output[:500]}...
```

## Setup
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
'''
        }

    def _manual_file_extraction(self, output: str) -> Dict[str, str]:
        """Fallback file extraction if JSON parsing fails"""
        files = {}
        
        try:
            # Extract the content between ```json and ```
            if "```json" in output:
                start_idx = output.find("```json") + len("```json")
                end_idx = output.rfind("```")
                if end_idx > start_idx:
                    json_content = output[start_idx:end_idx].strip()
                else:
                    json_content = output[start_idx:].strip()
            else:
                json_content = output
            
            # Use regex to find file entries
            import re
            
            # Pattern to match file entries like "filename": "content"
            pattern = r'"([^"]+\.(?:py|md|txt|yml|yaml|json|sh|dockerfile|Dockerfile))"\s*:\s*"([^"]*(?:\\.[^"]*)*)"'
            
            matches = re.findall(pattern, json_content, re.DOTALL)
            
            for filename, content in matches:
                # Unescape the content
                content = content.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                files[filename] = content
                
        except Exception as e:
            print(f"Manual extraction failed: {e}")
            
        return files

    async def modify_project(
        self, 
        existing_files: Dict[str, str], 
        modification_prompt: str
    ) -> Dict[str, str]:
        """Modify existing project based on user request"""
        
        if not HF_AVAILABLE or not self.client:
            return self._generate_fallback_modification(existing_files, modification_prompt)
        
        # Format prompt for iteration
        prompt = f"""### Existing Project Files:
{json.dumps(existing_files, indent=2)}

### Modification Request:
{modification_prompt}

### Instructions:
Modify the existing files as requested. Return the complete updated files dictionary.
Only include files that need to be changed or added.

### Output Format:
Return JSON with:
{{
  "files": {{ "path/to/file.py": "<updated code>", ... }}
}}"""

        try:
            output = await self._generate_with_hf(prompt)
            files = self._parse_generated_output(output)
            return files
            
        except Exception as e:
            print(f"Error during modification: {e}")
            return self._generate_fallback_modification(existing_files, modification_prompt)

        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, self._generate, prompt)
        
        modified_files = self._parse_generated_output(output)
        
        # Merge with existing files
        result = existing_files.copy()
        result.update(modified_files)
        
        return result

    def _generate_fallback_project(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate a basic project structure when AI models are not available"""
        
        project_name = context.get('name', 'fastapi_project')
        description = context.get('description', 'A FastAPI project')
        
        # Basic FastAPI project template
        files = {
            "main.py": f'''"""
{description}
"""

from fastapi import FastAPI

app = FastAPI(
    title="{project_name}",
    description="{description}",
    version="1.0.0"
)


@app.get("/")
async def read_root():
    """Root endpoint"""
    return {{"message": "Hello World", "project": "{project_name}"}}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {{"status": "healthy"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''',
            "requirements.txt": '''fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
''',
            "README.md": f'''# {project_name}

{description}

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
uvicorn main:app --reload
```

## API Documentation

Visit http://localhost:8000/docs for interactive API documentation.
''',
            ".gitignore": '''__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.env
.venv
.DS_Store
''',
        }
        
        return files

    def _generate_fallback_modification(
        self, 
        existing_files: Dict[str, str], 
        modification_prompt: str
    ) -> Dict[str, str]:
        """Generate basic modifications when AI models are not available"""
        
        # Return empty dict indicating no modifications could be made
        return {}

    async def cleanup(self):
        """Cleanup model resources"""
        # No cleanup needed for HF Inference API
        pass