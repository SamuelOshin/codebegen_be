"""
Mistral-7B-Instruct model wrapper for documentation generation.
Handles API documentation, setup guides, and architectural documentation.
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: Transformers/PyTorch not available. Documentation generation will be limited.")

from app.core.config import settings


class MistralDocsGenerator:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model: Optional[AutoModelForCausalLM] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    async def load(self):
        """Load Mistral model for documentation generation"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model)

    def _load_model(self):
        """Synchronous model loading"""
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, 
            trust_remote_code=True,
            use_fast=True
        )
        
        # Set pad token if not present
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            device_map="auto",
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        
        print(f"Loaded Mistral docs generator model: {self.model_path}")

    async def generate_documentation(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any],
        project_context: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """Generate comprehensive documentation for the project"""
        
        if project_context is None:
            project_context = {}
        
        documentation = {}
        
        # Generate different types of documentation
        doc_types = [
            ("README.md", self._generate_readme),
            ("API_DOCUMENTATION.md", self._generate_api_docs),
            ("SETUP_GUIDE.md", self._generate_setup_guide),
            ("DEPLOYMENT_GUIDE.md", self._generate_deployment_guide),
            ("ARCHITECTURE.md", self._generate_architecture_docs)
        ]
        
        for doc_name, generator_func in doc_types:
            try:
                content = await generator_func(files, schema, project_context)
                documentation[doc_name] = content
            except Exception as e:
                print(f"Error generating {doc_name}: {e}")
                documentation[doc_name] = f"# {doc_name}\n\nError generating documentation: {e}"
        
        return documentation

    async def _generate_readme(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Generate comprehensive README.md"""
        
        prompt = self._format_readme_prompt(files, schema, context)
        
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, self._generate_content, prompt)
        
        return self._extract_markdown_content(output)

    async def _generate_api_docs(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Generate API documentation"""
        
        prompt = self._format_api_docs_prompt(files, schema, context)
        
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, self._generate_content, prompt)
        
        return self._extract_markdown_content(output)

    async def _generate_setup_guide(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Generate setup and installation guide"""
        
        prompt = self._format_setup_guide_prompt(files, schema, context)
        
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, self._generate_content, prompt)
        
        return self._extract_markdown_content(output)

    async def _generate_deployment_guide(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Generate deployment guide"""
        
        prompt = self._format_deployment_guide_prompt(files, schema, context)
        
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, self._generate_content, prompt)
        
        return self._extract_markdown_content(output)

    async def _generate_architecture_docs(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Generate architecture documentation"""
        
        prompt = self._format_architecture_prompt(files, schema, context)
        
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, self._generate_content, prompt)
        
        return self._extract_markdown_content(output)

    def _format_readme_prompt(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Format prompt for README generation"""
        
        # Extract key information
        project_name = context.get("project_name", "FastAPI Project")
        domain = context.get("domain", "general")
        tech_stack = context.get("tech_stack", "fastapi_postgres")
        
        # Analyze files to understand structure
        has_docker = "Dockerfile" in files or "docker-compose.yml" in files
        has_tests = any("test" in filename for filename in files.keys())
        endpoints = self._extract_endpoints_from_files(files)
        
        system_prompt = """You are a technical documentation expert. Generate a comprehensive, professional README.md file for a FastAPI project.

Include:
- Project title and description
- Features list
- Installation instructions
- Usage examples
- API endpoints overview
- Contributing guidelines
- License information

Write in clear, professional markdown format."""

        user_prompt = f"""### Project Information:
- Name: {project_name}
- Domain: {domain}
- Tech Stack: {tech_stack}
- Has Docker: {has_docker}
- Has Tests: {has_tests}

### Database Schema:
{json.dumps(schema, indent=2)}

### API Endpoints:
{json.dumps(endpoints, indent=2)}

### Project Structure:
{list(files.keys())}

Generate a comprehensive README.md file that explains this FastAPI project clearly and professionally. Include installation instructions, usage examples, and feature descriptions.

Write the complete README content in markdown format:"""

        return f"{system_prompt}\n\n{user_prompt}"

    def _format_api_docs_prompt(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Format prompt for API documentation"""
        
        endpoints = self._extract_endpoints_from_files(files)
        models = schema.get("entities", [])
        
        system_prompt = """You are an API documentation specialist. Generate comprehensive API documentation for a FastAPI project.

Include:
- API overview and base URL
- Authentication details
- Endpoint documentation with parameters
- Request/response examples
- Error codes and handling
- Rate limiting information

Write in professional markdown format with clear examples."""

        user_prompt = f"""### API Information:
- Framework: FastAPI
- Authentication: JWT (if applicable)

### Database Models:
{json.dumps(models, indent=2)}

### API Endpoints:
{json.dumps(endpoints, indent=2)}

### Available Files:
{list(files.keys())}

Generate comprehensive API documentation that developers can use to integrate with this API. Include request/response examples and error handling information.

Write the complete API documentation in markdown format:"""

        return f"{system_prompt}\n\n{user_prompt}"

    def _format_setup_guide_prompt(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Format prompt for setup guide"""
        
        has_docker = "Dockerfile" in files or "docker-compose.yml" in files
        has_requirements = "requirements.txt" in files or "pyproject.toml" in files
        tech_stack = context.get("tech_stack", "fastapi_postgres")
        
        system_prompt = """You are a developer onboarding specialist. Generate a detailed setup and installation guide for a FastAPI project.

Include:
- Prerequisites and system requirements
- Step-by-step installation instructions
- Environment configuration
- Database setup
- Running the application
- Troubleshooting common issues

Write clear, actionable instructions that any developer can follow."""

        user_prompt = f"""### Project Setup Information:
- Tech Stack: {tech_stack}
- Has Docker: {has_docker}
- Has Requirements File: {has_requirements}
- Database: PostgreSQL (if postgres in tech_stack)

### Project Files:
{list(files.keys())}

### Database Schema:
{json.dumps(schema.get("entities", [])[:3], indent=2)}  # First 3 entities

Generate a comprehensive setup guide that helps developers get this FastAPI project running locally. Include prerequisites, installation steps, and configuration instructions.

Write the complete setup guide in markdown format:"""

        return f"{system_prompt}\n\n{user_prompt}"

    def _format_deployment_guide_prompt(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Format prompt for deployment guide"""
        
        has_docker = "Dockerfile" in files or "docker-compose.yml" in files
        
        system_prompt = """You are a DevOps engineer. Generate a comprehensive deployment guide for a FastAPI application.

Include:
- Production deployment options
- Environment configuration
- Database migrations
- Security considerations
- Monitoring and logging
- Scaling strategies

Write practical, production-ready deployment instructions."""

        user_prompt = f"""### Deployment Context:
- Framework: FastAPI
- Has Docker: {has_docker}
- Database: PostgreSQL (likely)
- Authentication: JWT (likely)

### Project Files:
{list(files.keys())}

Generate a comprehensive deployment guide covering different deployment scenarios (Docker, cloud platforms, VPS). Include security best practices and monitoring setup.

Write the complete deployment guide in markdown format:"""

        return f"{system_prompt}\n\n{user_prompt}"

    def _format_architecture_prompt(
        self, 
        files: Dict[str, str], 
        schema: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> str:
        """Format prompt for architecture documentation"""
        
        entities = schema.get("entities", [])
        relationships = schema.get("relationships", [])
        
        system_prompt = """You are a software architect. Generate comprehensive architecture documentation for a FastAPI project.

Include:
- System overview and design principles
- Component architecture
- Database design and relationships
- API design patterns
- Security architecture
- Scalability considerations

Write technical but accessible documentation for developers and architects."""

        user_prompt = f"""### Architecture Information:
- Framework: FastAPI with clean architecture
- Pattern: Repository pattern, service layer separation

### Database Entities:
{json.dumps(entities, indent=2)}

### Entity Relationships:
{json.dumps(relationships, indent=2)}

### Project Structure:
{list(files.keys())}

Generate comprehensive architecture documentation explaining the system design, patterns used, and architectural decisions made in this FastAPI project.

Write the complete architecture documentation in markdown format:"""

        return f"{system_prompt}\n\n{user_prompt}"

    def _generate_content(self, prompt: str) -> str:
        """Synchronous content generation"""
        inputs = self.tokenizer(
            prompt, 
            return_tensors="pt", 
            truncation=True, 
            max_length=3072
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=2048,
                temperature=0.3,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        generated = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:], 
            skip_special_tokens=True
        )
        
        return generated

    def _extract_markdown_content(self, output: str) -> str:
        """Extract and clean markdown content from model output"""
        # Remove any prompt remnants
        lines = output.split('\n')
        cleaned_lines = []
        in_content = False
        
        for line in lines:
            # Start collecting after we see markdown headers
            if line.strip().startswith('#') and not in_content:
                in_content = True
            
            if in_content:
                cleaned_lines.append(line)
        
        if not cleaned_lines:
            # Fallback: return the entire output
            return output.strip()
        
        content = '\n'.join(cleaned_lines).strip()
        
        # Ensure it starts with a header if it doesn't
        if not content.startswith('#'):
            content = "# Project Documentation\n\n" + content
        
        return content

    def _extract_endpoints_from_files(self, files: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract API endpoints from code files"""
        endpoints = []
        
        for file_path, content in files.items():
            if file_path.endswith('.py') and ('router' in file_path or 'main.py' in file_path):
                # Look for FastAPI route decorators
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    line_stripped = line.strip()
                    
                    # Match route decorators
                    route_patterns = [
                        r'@\w+\.get\(["\']([^"\']+)["\']',
                        r'@\w+\.post\(["\']([^"\']+)["\']',
                        r'@\w+\.put\(["\']([^"\']+)["\']',
                        r'@\w+\.delete\(["\']([^"\']+)["\']',
                        r'@\w+\.patch\(["\']([^"\']+)["\']'
                    ]
                    
                    for pattern in route_patterns:
                        match = re.search(pattern, line_stripped)
                        if match:
                            method = pattern.split('.')[1].split('\\')[0].upper()
                            path = match.group(1)
                            
                            # Try to find function description
                            description = ""
                            if i + 1 < len(lines):
                                next_line = lines[i + 1].strip()
                                if next_line.startswith('async def ') or next_line.startswith('def '):
                                    func_name = next_line.split('(')[0].replace('async def ', '').replace('def ', '')
                                    description = func_name.replace('_', ' ').title()
                            
                            endpoints.append({
                                "path": path,
                                "method": method,
                                "description": description or f"{method} {path}",
                                "file": file_path
                            })
                            break
        
        return endpoints

    async def cleanup(self):
        """Cleanup model resources"""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        torch.cuda.empty_cache()
        print("Mistral docs generator cleanup completed")
