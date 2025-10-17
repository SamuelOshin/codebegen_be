"""
Google Gemini Provider Implementation

Implements the BaseLLMProvider interface using Google's Gemini 2.5 Pro model
for all AI tasks: schema extraction, code generation, code review, and documentation.
"""

import json
import re
import logging
from typing import Dict, Any, Optional

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("google-generativeai not available. Gemini provider will not work.")

from .base_provider import BaseLLMProvider, LLMTask
from app.core.config import settings


logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini 2.5 Pro provider for all AI code generation tasks.
    
    This provider uses a single powerful model (Gemini) for all tasks instead of
    multiple specialized models, simplifying the architecture while maintaining quality.
    """
    
    def __init__(self):
        self.client = None
        self.model = None
        self.initialized = False
        self._generation_config = None
        self._safety_settings = None
    
    async def initialize(self) -> None:
        """Initialize Gemini API client and configuration"""
        if self.initialized:
            return
        
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )
        
        if not settings.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY not configured. "
                "Set GOOGLE_API_KEY environment variable or in .env file"
            )
        
        try:
            # Configure API
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            
            # Configure safety settings (permissive for code generation)
            self._safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # Initialize model
            self.model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                safety_settings=self._safety_settings
            )
            
            self.initialized = True
            logger.info(f"✅ Gemini Provider initialized successfully: {settings.GEMINI_MODEL}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini provider: {e}")
            raise
    
    async def generate_completion(
        self,
        prompt: str,
        task: LLMTask,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate completion using Gemini API"""
        
        if not self.initialized:
            await self.initialize()
        
        try:
            # Build generation config
            config_params = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "top_p": kwargs.get('top_p', settings.GEMINI_TOP_P),
                "top_k": kwargs.get('top_k', settings.GEMINI_TOP_K)
            }
            
            # Try to use JSON mode for structured tasks (if supported by model)
            # Note: response_mime_type may not be supported by all models
            if task in [LLMTask.SCHEMA_EXTRACTION, LLMTask.CODE_GENERATION]:
                try:
                    config_params["response_mime_type"] = "application/json"
                    logger.debug("Enabling JSON response mode")
                except Exception:
                    logger.debug("JSON response mode not supported, using text mode")
            
            generation_config = genai.types.GenerationConfig(**config_params)
            
            logger.debug(f"Generating completion for {task} with max_tokens={max_tokens}")
            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config
            )
            
            response_text = response.text
            logger.info(f"✅ Received response: {len(response_text)} characters")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Gemini completion failed for task {task}: {e}")
            raise
    
    async def extract_schema(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract schema using Gemini with specialized prompt"""
        
        tech_stack = context.get('tech_stack', 'fastapi_postgres')
        domain = context.get('domain', 'general')
        
        schema_prompt = f"""You are an expert database architect and API designer.

TASK: Analyze the following project description and extract a comprehensive database schema and API structure.

PROJECT DESCRIPTION:
{prompt}

DOMAIN: {domain}
TECH STACK: {tech_stack}

ADDITIONAL CONTEXT:
{json.dumps(context, indent=2)}

OUTPUT REQUIREMENTS:
Generate a JSON object with the following structure:

{{
    "entities": [
        {{
            "name": "EntityName",
            "description": "Brief description",
            "fields": [
                {{
                    "name": "field_name",
                    "type": "string|integer|float|boolean|datetime|text|json",
                    "required": true,
                    "unique": false,
                    "indexed": false,
                    "description": "Field purpose"
                }}
            ],
            "relationships": [
                {{
                    "type": "one_to_many|many_to_one|many_to_many",
                    "target": "TargetEntity",
                    "description": "Relationship purpose"
                }}
            ]
        }}
    ],
    "endpoints": [
        {{
            "path": "/api/resource",
            "method": "GET|POST|PUT|PATCH|DELETE",
            "description": "Endpoint description",
            "entity": "EntityName",
            "requires_auth": true
        }}
    ],
    "tech_stack": "{tech_stack}",
    "database_type": "postgresql",
    "authentication": "JWT"
}}

CRITICAL: Return ONLY the JSON object. No markdown code blocks, no explanations, just valid JSON."""

        try:
            response = await self.generate_completion(
                schema_prompt,
                task=LLMTask.SCHEMA_EXTRACTION,
                temperature=0.3,  # Lower temperature for structured output
                max_tokens=4096
            )
            
            return self._extract_json(response)
            
        except Exception as e:
            logger.error(f"Schema extraction failed: {e}")
            # Return a minimal schema as fallback
            return {
                "entities": [],
                "endpoints": [],
                "tech_stack": tech_stack,
                "error": str(e)
            }
    
    async def generate_code(
        self,
        prompt: str,
        schema: Dict[str, Any],
        context: Dict[str, Any],
        file_manager: Any = None,
        generation_id: str = None,
        event_callback: Any = None
    ) -> Dict[str, str]:
        """
        Generate complete project code using either phased or simple generation.
        
        Automatically selects strategy based on complexity:
        - Iteration: For project modifications (context-aware editing)
        - Phased: For 3+ entities or when repository pattern requested
        - Simple: For 1-2 entities with basic requirements
        
        Args:
            prompt: User's generation request
            schema: Parsed schema with entities and relationships
            context: Additional context (tech_stack, complexity, etc.)
            file_manager: FileManager instance for saving files incrementally
            generation_id: Unique ID for this generation (for file storage)
            event_callback: Callback for emitting progress events
        """
        
        # ✅ CRITICAL FIX: Check for iteration mode
        is_iteration = context.get('is_iteration', False)
        if is_iteration:
            logger.info(f"[Iteration Mode] Using focused generation for project modification")
            print(f"\n{'='*80}")
            print(f"🔄 STRATEGY: Iteration Mode")
            print(f"📊 Context: Modifying existing project")
            print(f"{'='*80}\n")
            
            # Emit event for iteration mode
            if event_callback and context.get('generation_id'):
                await event_callback(context.get('generation_id'), {
                    "status": "processing",
                    "stage": "iteration_mode",
                    "message": "Using iteration mode for focused changes",
                    "progress": 35
                })
            
            # Use iteration-focused generation (simpler, more precise)
            return await self._generate_iteration_changes(prompt, schema, context, event_callback)
        
        entities = schema.get('entities', [])
        entity_count = len(entities)
        use_repository_pattern = context.get('use_repository_pattern', True)
        complexity = context.get('complexity', 'medium')
        
        # Decide strategy for new projects
        use_phased_generation = (
            entity_count >= 3 or  # 3 or more entities
            use_repository_pattern or  # Repository pattern requested
            complexity == 'high' or  # High complexity project
            context.get('force_phased', False)  # Explicitly requested
        )
        
        if use_phased_generation:
            print(f"\n{'='*80}")
            print(f"🎯 STRATEGY: Phased Generation")
            print(f"📊 Reason: {entity_count} entities, repository pattern={'enabled' if use_repository_pattern else 'disabled'}")
            print(f"{'='*80}\n")
            
            logger.info(f"Using phased generation for {entity_count} entities")
            
            # Use phased generator with file saving
            from .gemini_phased_generator import GeminiPhasedGenerator
            phased_generator = GeminiPhasedGenerator(self, file_manager=file_manager, event_callback=event_callback)
            return await phased_generator.generate_complete_project(
                prompt, schema, context, generation_id=generation_id
            )
        
        else:
            print(f"\n{'='*80}")
            print(f"⚡ STRATEGY: Simple Generation")
            print(f"📊 Reason: {entity_count} entities, basic requirements")
            print(f"{'='*80}\n")
            
            logger.info(f"Using simple generation for {entity_count} entities")
            
            # Use simple generator
            return await self._generate_simple_project(prompt, schema, context)
    
    async def _generate_simple_project(
        self,
        prompt: str,
        schema: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate a simple project for 1-2 entities (legacy simplified approach)"""
        
        tech_stack = context.get('tech_stack', 'fastapi_postgres')
        entities = schema.get('entities', [])
        
        # Limit entities to avoid overwhelming the model
        entity_names = [e.get('name', '') for e in entities[:2]]  # Max 2 entities for simple
        
        code_prompt = f"""Generate a FastAPI project structure as a JSON object.

PROJECT: {prompt}

ENTITIES: {', '.join(entity_names)}

Return ONLY this JSON structure with complete working code (no markdown, no explanations):

{{
  "main.py": "complete FastAPI app code with CORS and routers",
  "app/__init__.py": "",
  "app/core/config.py": "Pydantic Settings with DATABASE_URL, SECRET_KEY, etc",
  "app/core/database.py": "SQLAlchemy async engine and session",
  "app/core/security.py": "password hashing and JWT token functions",
  "app/models/__init__.py": "import all models",
  "app/schemas/__init__.py": "import all schemas",
  "app/routers/__init__.py": "import all routers",
  "requirements.txt": "fastapi, uvicorn, sqlalchemy, pydantic, etc",
  "README.md": "Setup and run instructions"
}}

Add a model, schema, and router file for each entity: {', '.join(entity_names[:3])}

Keep code concise but functional. Include only essential files."""

        try:
            print(f"\n{'='*80}")
            print(f"🚀 GEMINI CODE GENERATION STARTED")
            print(f"{'='*80}")
            print(f"📝 Prompt: {prompt[:100]}...")
            print(f"📊 Entities: {', '.join(entity_names)}")
            print(f"⚙️  Tech Stack: {tech_stack}")
            print(f"{'='*80}\n")
            
            logger.info(f"🚀 Starting code generation with Gemini...")
            logger.info(f"📊 Entities: {', '.join(entity_names)}")
            
            response = await self.generate_completion(
                code_prompt,
                task=LLMTask.CODE_GENERATION,
                temperature=0.3,  # Lower temperature for more focused output
                max_tokens=8192  # Gemini 2.0's max output tokens
            )
            
            print(f"\n✅ Received Gemini response: {len(response)} characters\n")
            logger.info(f"✅ Received response: {len(response)} characters")
            logger.debug(f"📄 Response preview: {response[:300]}...")
            
            # Parse the JSON response
            print(f"🔄 Parsing JSON response...")
            parsed_files = self._extract_json(response)
            
            # Validate that we got a dictionary of files
            if not isinstance(parsed_files, dict):
                logger.error(f"Gemini returned non-dict response: {type(parsed_files)}")
                raise ValueError("Expected dictionary of files from Gemini")
            
            # Ensure we have at least some files
            if not parsed_files:
                logger.warning("Gemini returned empty files dictionary")
                raise ValueError("No files generated by Gemini")
            
            print(f"✅ Successfully generated {len(parsed_files)} files")
            print(f"📁 Files: {', '.join(list(parsed_files.keys())[:10])}")
            if len(parsed_files) > 10:
                print(f"   ... and {len(parsed_files) - 10} more files")
            print(f"{'='*80}\n")
            
            logger.info(f"✅ Successfully generated {len(parsed_files)} files")
            return parsed_files
            
        except ValueError as e:
            logger.error(f"Code generation failed - JSON parsing error: {e}")
            raise
        except Exception as e:
            logger.error(f"Code generation failed - unexpected error: {e}")
            raise
    
    async def _generate_iteration_changes(
        self,
        prompt: str,
        schema: Dict[str, Any],
        context: Dict[str, Any],
        event_callback: Any = None
    ) -> Dict[str, str]:
        """
        Generate focused changes for project iterations.
        
        Uses lower temperature and simpler approach for precise edits.
        The prompt should already contain context about existing files.
        """
        
        tech_stack = context.get('tech_stack', 'fastapi_postgres')
        iteration_intent = context.get('iteration_intent', 'modify')
        existing_file_count = context.get('existing_file_count', 0)
        generation_id = context.get('generation_id')
        
        logger.info(f"[Iteration] Generating changes with intent: {iteration_intent}")
        
        if event_callback and generation_id:
            await event_callback(generation_id, {
                "status": "processing",
                "stage": "llm_generation",
                "message": f"Sending request to Gemini ({iteration_intent})...",
                "progress": 50
            })
        
        # The prompt already contains context from iterate_project()
        # We just need to ensure focused, precise generation
        iteration_prompt = f"""{prompt}

IMPORTANT ITERATION RULES:
1. Return ONLY files that need to be added or modified
2. Do NOT regenerate unchanged files
3. Ensure changes integrate with existing project structure
4. Use the same coding patterns and conventions as existing files
5. Return as JSON: {{"filepath": "complete file content", ...}}

Return ONLY valid JSON with the new/modified files.
No markdown, no explanations, just the JSON object.
"""
        
        try:
            logger.info("[Iteration] Sending iteration request to Gemini")
            
            if event_callback and generation_id:
                await event_callback(generation_id, {
                    "status": "processing",
                    "stage": "gemini_processing",
                    "message": "Waiting for Gemini response...",
                    "progress": 60
                })
            
            result = await self.model.generate_content_async(
                iteration_prompt,
                generation_config={
                    "temperature": 0.3,  # Lower temperature for precise edits
                    "max_output_tokens": 8000,
                    "top_p": 0.8,
                    "top_k": 20
                }
            )
            
            response = result.text
            logger.info(f"[Iteration] Received response ({len(response)} chars)")
            
            if event_callback and generation_id:
                await event_callback(generation_id, {
                    "status": "processing",
                    "stage": "parsing_response",
                    "message": "Parsing generated files...",
                    "progress": 70
                })
            
            # Parse JSON response
            parsed_files = self._extract_json(response)
            
            if not isinstance(parsed_files, dict):
                logger.error(f"[Iteration] Non-dict response: {type(parsed_files)}")
                raise ValueError("Expected dictionary of files from Gemini")
            
            if not parsed_files:
                logger.warning("[Iteration] Empty files dictionary returned")
                return {}
            
            print(f"✅ [Iteration] Generated {len(parsed_files)} file changes")
            print(f"📁 Files: {', '.join(list(parsed_files.keys()))}")
            print(f"{'='*80}\n")
            
            logger.info(f"✅ [Iteration] Successfully generated {len(parsed_files)} file changes")
            return parsed_files
            
        except ValueError as e:
            logger.error(f"[Iteration] JSON parsing error: {e}")
            raise
        except Exception as e:
            logger.error(f"[Iteration] Unexpected error: {e}")
            raise
    
    async def review_code(
        self,
        files: Dict[str, str]
    ) -> Dict[str, Any]:
        """Review code using Gemini"""
        
        # Prepare file contents (limit each file to prevent token overflow)
        files_summary = []
        for path, content in list(files.items())[:20]:  # Limit to 20 files
            truncated_content = content[:2000] if len(content) > 2000 else content
            files_summary.append(f"=== {path} ===\n{truncated_content}")
        
        files_content = "\n\n".join(files_summary)
        
        review_prompt = f"""You are a senior code reviewer with expertise in Python, FastAPI, security, and best practices.

TASK: Review the following code for quality, security, performance, and best practices.

CODE FILES:
{files_content}

ANALYSIS CRITERIA:
1. Security Vulnerabilities:
   - SQL injection risks
   - XSS vulnerabilities
   - Hardcoded secrets
   - Insecure authentication
   - Missing input validation

2. Code Quality:
   - Naming conventions
   - Code duplication
   - Function complexity
   - Proper use of design patterns
   - Type hints coverage

3. Performance Issues:
   - N+1 query problems
   - Inefficient algorithms
   - Missing database indexes
   - Unnecessary computations

4. Best Practices:
   - Error handling
   - Logging practices
   - Documentation completeness
   - Test coverage indicators
   - Configuration management

OUTPUT FORMAT:
Return a JSON object with this exact structure:

{{
    "issues": [
        {{
            "file": "path/to/file.py",
            "line": 42,
            "severity": "high|medium|low",
            "category": "security|performance|quality|style",
            "message": "Clear description of the issue",
            "code": "ISSUE_CODE_NAME",
            "suggestion": "How to fix this issue"
        }}
    ],
    "suggestions": [
        {{
            "file": "path/to/file.py",
            "category": "improvement|optimization|refactoring",
            "message": "Improvement suggestion with specific recommendations"
        }}
    ],
    "scores": {{
        "security": 0.85,
        "maintainability": 0.90,
        "performance": 0.88,
        "overall": 0.88
    }},
    "summary": "Brief overall assessment of code quality"
}}

CRITICAL: Return ONLY valid JSON. No markdown, no explanations."""

        try:
            response = await self.generate_completion(
                review_prompt,
                task=LLMTask.CODE_REVIEW,
                temperature=0.3,  # Low temperature for consistent analysis
                max_tokens=4096
            )
            
            return self._extract_json(response)
            
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            # Return minimal review on failure
            return {
                "issues": [],
                "suggestions": [],
                "scores": {
                    "security": 0.7,
                    "maintainability": 0.7,
                    "performance": 0.7,
                    "overall": 0.7
                },
                "summary": f"Review failed: {str(e)}"
            }
    
    async def generate_documentation(
        self,
        files: Dict[str, str],
        schema: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate comprehensive documentation using Gemini"""
        
        docs = {}
        
        # Generate README.md
        readme_prompt = self._create_readme_prompt(files, schema, context)
        docs["README.md"] = await self.generate_completion(
            readme_prompt,
            task=LLMTask.DOCUMENTATION,
            temperature=0.5,
            max_tokens=3000
        )
        
        # Generate API_DOCUMENTATION.md
        api_docs_prompt = self._create_api_docs_prompt(files, schema, context)
        docs["API_DOCUMENTATION.md"] = await self.generate_completion(
            api_docs_prompt,
            task=LLMTask.DOCUMENTATION,
            temperature=0.5,
            max_tokens=3000
        )
        
        # Generate SETUP_GUIDE.md
        setup_prompt = self._create_setup_guide_prompt(files, schema, context)
        docs["SETUP_GUIDE.md"] = await self.generate_completion(
            setup_prompt,
            task=LLMTask.DOCUMENTATION,
            temperature=0.5,
            max_tokens=2000
        )
        
        return docs
    
    def _extract_json(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from response with robust error handling.
        
        Handles:
        - Markdown code blocks
        - Truncated responses
        - Escaped strings
        - Multiple JSON objects
        """
        original_response = response
        
        # Step 1: Remove markdown code blocks
        response = re.sub(r'^```(?:json)?\s*', '', response, flags=re.MULTILINE)
        response = re.sub(r'^```\s*$', '', response, flags=re.MULTILINE)
        response = response.strip()
        
        # Step 2: Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Direct JSON parse failed: {e}")
        
        # Step 3: Try to find the first complete JSON object
        try:
            # Find the start of JSON
            start_idx = response.find('{')
            if start_idx == -1:
                raise ValueError("No JSON object found in response")
            
            # Count braces to find the end
            brace_count = 0
            in_string = False
            escape_next = False
            end_idx = -1
            
            for i in range(start_idx, len(response)):
                char = response[i]
                
                # Handle escape sequences
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                
                # Handle strings
                if char == '"':
                    in_string = not in_string
                    continue
                
                # Count braces outside of strings
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
            
            if end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                try:
                    result = json.loads(json_str)
                    print(f"✅ JSON extracted using brace matching")
                    logger.info("✅ Successfully extracted JSON using brace matching")
                    return result
                except json.JSONDecodeError as e:
                    print(f"⚠️  Brace-matched JSON still invalid: {e}")
                    logger.warning(f"Brace-matched JSON still invalid: {e}")
        
        except Exception as e:
            print(f"⚠️  Brace matching failed: {e}")
            logger.warning(f"Brace matching failed: {e}")
        
        # Step 4: Try regex-based extraction (last resort)
        try:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                print(f"✅ JSON extracted using regex")
                logger.info("✅ Successfully extracted JSON using regex")
                return result
        except Exception as e:
            print(f"⚠️  Regex extraction failed: {e}")
            logger.warning(f"Regex extraction failed: {e}")
        
        # Step 5: If all else fails, log detailed error and raise
        print(f"\n{'='*80}")
        print(f"❌ ALL JSON EXTRACTION METHODS FAILED")
        print(f"{'='*80}")
        print(f"Response length: {len(original_response)} characters")
        print(f"Response preview (first 300 chars):")
        print(original_response[:300])
        print(f"\nResponse ending (last 300 chars):")
        print(original_response[-300:])
        print(f"{'='*80}\n")
        
        logger.error(f"❌ All JSON extraction methods failed")
        logger.error(f"Response length: {len(original_response)}")
        logger.error(f"Response preview: {original_response[:200]}...")
        logger.error(f"Response ending: ...{original_response[-200:]}")
        
        raise ValueError(
            f"Failed to parse JSON from Gemini response. "
            f"Response appears to be malformed or truncated. "
            f"Length: {len(original_response)} chars. "
            f"The response was cut off. Try a simpler prompt."
        )
    
    def _create_readme_prompt(self, files, schema, context) -> str:
        """Create prompt for README generation"""
        project_name = context.get('project_name', 'Generated Project')
        tech_stack = context.get('tech_stack', 'fastapi_postgres')
        
        return f"""Generate a comprehensive README.md for this project.

PROJECT: {project_name}
TECH STACK: {tech_stack}
SCHEMA: {json.dumps(schema.get('entities', [])[:3], indent=2)}

Include:
1. Project title and description
2. Features list
3. Tech stack
4. Prerequisites
5. Installation steps
6. Configuration guide
7. Running the application
8. API endpoints overview
9. Testing instructions
10. Deployment notes
11. Contributing guidelines
12. License

Use clear markdown formatting. Be concise but complete."""
    
    def _create_api_docs_prompt(self, files, schema, context) -> str:
        """Create prompt for API documentation generation"""
        endpoints = schema.get('endpoints', [])
        
        return f"""Generate comprehensive API documentation.

ENDPOINTS:
{json.dumps(endpoints, indent=2)}

Include for each endpoint:
1. HTTP method and path
2. Description
3. Request parameters
4. Request body schema (if applicable)
5. Response schema
6. Status codes
7. Authentication requirements
8. Example requests with curl
9. Example responses

Use markdown tables and code blocks for clarity."""
    
    def _create_setup_guide_prompt(self, files, schema, context) -> str:
        """Create prompt for setup guide generation"""
        return f"""Generate a detailed setup and deployment guide.

TECH STACK: {context.get('tech_stack', 'fastapi_postgres')}

Include:
1. System requirements
2. Dependencies installation
3. Database setup and migrations
4. Environment configuration
5. Running in development mode
6. Running in production mode
7. Docker deployment (if applicable)
8. Troubleshooting common issues
9. Performance optimization tips
10. Security considerations

Be specific and actionable."""
    
    async def get_provider_info(self) -> Dict[str, Any]:
        """Get information about Gemini provider"""
        return {
            "name": "GeminiProvider",
            "type": "gemini",
            "models": {
                "primary": settings.GEMINI_MODEL
            },
            "capabilities": [
                "schema_extraction",
                "code_generation",
                "code_review",
                "documentation"
            ],
            "initialized": self.initialized,
            "unified_model": True,  # Uses single model for all tasks
            "context_window": "1M tokens",
            "supports_async": True
        }
