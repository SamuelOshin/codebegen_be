"""
Gemini 2.5 Pro model wrapper for code generation.
Handles prompt formatting and code generation via Google's Gemini API.
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("Warning: google-generativeai not available. Gemini code generation will be limited.")

from app.core.config import settings


class GeminiGenerator:
    """Gemini 2.5 Pro generator for code generation"""
    
    def __init__(self, model_name: str = "gemini-2.5-pro"):
        self.model_name = model_name
        self.model = None
        self.chat = None
        
        # Initialize Gemini
        if GENAI_AVAILABLE:
            try:
                # Get API key from environment or settings
                api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
                
                if api_key:
                    genai.configure(api_key=api_key)
                    
                    # Configure generation parameters
                    generation_config = {
                        "temperature": 0.1,
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": 8192,
                    }
                    
                    # Configure safety settings
                    safety_settings = [
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    ]
                    
                    self.model = genai.GenerativeModel(
                        model_name=self.model_name,
                        generation_config=generation_config,
                        safety_settings=safety_settings
                    )
                    
                    print(f"Gemini Generator initialized with model: {self.model_name}")
                else:
                    print("Warning: GEMINI_API_KEY not found in environment or settings")
                    self.model = None
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini: {e}")
                self.model = None

    async def load(self):
        """Initialize the Gemini model (already done in __init__)"""
        if not GENAI_AVAILABLE:
            print("Warning: Cannot initialize - google-generativeai not available")
            return
            
        if self.model is None:
            print("Warning: Gemini model not available - check GEMINI_API_KEY")
            return
            
        print("Gemini Generator ready for inference")

    async def generate_project(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate complete FastAPI project from prompt and schema"""
        
        if not GENAI_AVAILABLE or not self.model:
            return self._generate_fallback_project(prompt, schema, context)
        
        formatted_prompt = self._format_generation_prompt(prompt, schema, context)
        
        try:
            # Use Gemini API for generation
            output = await self._generate_with_gemini(formatted_prompt)
            
            # Parse output to extract files
            files = self._parse_generated_output(output)
            return files
            
        except Exception as e:
            print(f"Error during Gemini generation: {e}")
            return self._generate_fallback_project(prompt, schema, context)

    async def _generate_with_gemini(self, prompt: str) -> str:
        """Generate using Gemini API"""
        try:
            # Start a chat session for better context
            self.chat = self.model.start_chat(history=[])
            
            # Generate response
            response = await asyncio.to_thread(
                self.chat.send_message,
                prompt
            )
            
            return response.text
            
        except Exception as e:
            print(f"Gemini API error: {e}")
            raise

    async def generate_project_enhanced(
        self,
        architecture_prompt: str,
        implementation_prompt: str,
        schema: Dict[str, Any],
        domain: str,
        tech_stack: str
    ) -> Dict[str, str]:
        """Generate project with enhanced prompts for architecture and implementation"""
        
        if not GENAI_AVAILABLE or not self.model:
            # Fallback to basic generation
            return await self.generate_project(
                implementation_prompt, 
                schema, 
                {"domain": domain, "tech_stack": tech_stack}
            )
        
        # Combine architecture and implementation prompts
        combined_prompt = f"""### Architecture Planning:
{architecture_prompt}

### Implementation Requirements:
{implementation_prompt}

### Schema:
{json.dumps(schema, indent=2)}

### Technical Context:
Domain: {domain}
Tech Stack: {tech_stack}

Generate a complete, production-ready FastAPI project following the architecture plan.
"""
        
        try:
            output = await self._generate_with_gemini(combined_prompt)
            files = self._parse_generated_output(output)
            return files
        except Exception as e:
            print(f"Error in enhanced generation: {e}")
            return self._generate_fallback_project(
                implementation_prompt, 
                schema, 
                {"domain": domain, "tech_stack": tech_stack}
            )

    def _format_generation_prompt(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Format prompt for Gemini model"""
        
        system_instruction = """You are Codebegen, an expert AI backend engineer specializing in building production-ready FastAPI applications. Your expertise includes:
- Clean architecture and SOLID principles
- FastAPI best practices and async patterns
- SQLAlchemy 2.0 with async support
- Comprehensive error handling and validation
- Security best practices (JWT, password hashing, input validation)
- Comprehensive testing with pytest
- Production-ready configuration and deployment

Generate complete, working code that:
1. Follows PEP8 and uses proper type hints
2. Implements proper error handling
3. Includes comprehensive validation
4. Uses the latest FastAPI patterns
5. Has proper project structure (models, schemas, routers, services, repositories)
6. Includes tests and documentation
7. Is production-ready with proper configuration management
"""
        
        user_prompt = f"""{system_instruction}

### API Description:
{prompt}

### Extracted Schema:
{json.dumps(schema, indent=2)}

### Technical Context:
Domain: {context.get('domain', 'general')}
Tech Stack: {context.get('tech_stack', 'fastapi_postgres')}
Constraints: {', '.join(context.get('constraints', []))}

### Requirements:
- Follow PEP8 and use proper type hints
- Use the requested tech stack exactly
- Generate ALL required files for a working project
- Include Dockerfile and docker-compose.yml when applicable
- Ensure code runs without syntax errors
- Never invent package names - use only real, existing packages
- Always separate concerns into models, schemas, routers, services, and repositories
- Include basic tests and comprehensive README.md
- Implement proper authentication and authorization
- Add input validation and error handling
- Use async/await patterns throughout

### Output Format:
Return ONLY a JSON object with this exact structure:
{{
  "files": {{
    "path/to/file.py": "full file content here",
    "another/file.py": "full file content here"
  }}
}}

Do not include any explanations, markdown formatting, or additional text. Only return the JSON object.
"""

        return user_prompt

    def _parse_generated_output(self, output: str) -> Dict[str, str]:
        """Parse Gemini output to extract file dictionary with robust error handling"""
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
            elif "```" in output:
                # Handle case where there's just ``` without json
                start_idx = output.find("```") + 3
                end_idx = output.rfind("```")
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
            "main.py": '''"""FastAPI application generated by Gemini."""

from fastapi import FastAPI

app = FastAPI(title="Generated API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
''',
            "requirements.txt": '''fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
''',
            "README.md": f'''# Generated Project

This project was generated using Gemini 2.5 Pro but had parsing issues.

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
        
        if not GENAI_AVAILABLE or not self.model:
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
Return ONLY a JSON object with this exact structure:
{{
  "files": {{
    "path/to/file.py": "updated full file content",
    "new/file.py": "new file content"
  }}
}}

Do not include any explanations or markdown. Only return the JSON object.
"""

        try:
            output = await self._generate_with_gemini(prompt)
            files = self._parse_generated_output(output)
            return files
            
        except Exception as e:
            print(f"Error during modification: {e}")
            return self._generate_fallback_modification(existing_files, modification_prompt)

    def _generate_fallback_project(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate a basic project structure when Gemini is not available"""
        
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
        """Generate basic modifications when Gemini is not available"""
        # Return empty dict indicating no modifications could be made
        return {}

    async def cleanup(self):
        """Cleanup resources"""
        # Close chat session if exists
        if self.chat:
            self.chat = None
        print("Gemini generator cleanup completed")
