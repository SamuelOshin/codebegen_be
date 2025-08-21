"""
File search and content services for generation endpoints.
"""

import os
import re
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
import mimetypes

from app.schemas.generation import (
    GenerationFileResponse, GenerationSearchRequest, GenerationSearchResponse,
    SearchMatch, TemplateSearchRequest, TemplateSearchResponse, TemplateInfo
)
from app.services.file_manager import file_manager
from app.services.template_selector import TemplateSelector


class GenerationFileService:
    """Service for accessing individual generation files."""
    
    def __init__(self):
        self.max_file_size = 10 * 1024 * 1024  # 10MB limit
        self.binary_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.exe', '.dll', '.so', '.dylib'
        }
    
    async def get_file_content(self, generation_id: str, file_path: str) -> GenerationFileResponse:
        """Get content of a specific file from generation."""
        # Security: Validate file path to prevent directory traversal
        safe_path = self._validate_file_path(file_path)
        
        # Get generation directory
        generation_dir = await file_manager.get_generation_directory(generation_id)
        if not generation_dir or not generation_dir.exists():
            raise FileNotFoundError("Generation directory not found")
        
        # Construct full file path
        full_path = generation_dir / safe_path
        
        # Ensure file exists and is within generation directory
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not self._is_path_safe(full_path, generation_dir):
            raise ValueError("Invalid file path")
        
        # Check file size
        file_size = full_path.stat().st_size
        if file_size > self.max_file_size:
            raise ValueError(f"File too large: {file_size} bytes")
        
        # Determine if file is binary
        file_ext = full_path.suffix.lower()
        is_binary = file_ext in self.binary_extensions
        
        if is_binary:
            raise ValueError("Binary files are not supported")
        
        # Read file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(full_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                encoding = 'latin-1'
            except Exception:
                raise ValueError("Unable to decode file content")
        else:
            encoding = 'utf-8'
        
        # Determine file type and language
        file_type = mimetypes.guess_type(str(full_path))[0] or 'text/plain'
        language = self._detect_language(full_path)
        
        return GenerationFileResponse(
            path=file_path,
            content=content,
            file_type=file_type,
            size=file_size,
            encoding=encoding,
            language=language,
            last_modified=full_path.stat().st_mtime
        )
    
    def _validate_file_path(self, file_path: str) -> str:
        """Validate and sanitize file path."""
        # Remove leading slash and normalize
        clean_path = file_path.lstrip('/')
        
        # Check for directory traversal attempts
        if '..' in clean_path or clean_path.startswith('/'):
            raise ValueError("Invalid file path")
        
        return clean_path
    
    def _is_path_safe(self, full_path: Path, base_dir: Path) -> bool:
        """Check if the resolved path is within the base directory."""
        try:
            full_path.resolve().relative_to(base_dir.resolve())
            return True
        except ValueError:
            return False
    
    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension."""
        ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sql': 'sql',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'ini',
            '.conf': 'conf',
            '.md': 'markdown',
            '.txt': 'text',
            '.sh': 'bash',
            '.bat': 'batch',
            '.ps1': 'powershell',
            '.dockerfile': 'dockerfile'
        }
        
        return ext_to_lang.get(file_path.suffix.lower())


class GenerationSearchService:
    """Service for searching within generation files."""
    
    def __init__(self):
        self.max_files_to_search = 1000
        self.max_file_size = 1024 * 1024  # 1MB per file for search
        self.context_lines = 2
    
    async def search_generation(
        self, 
        generation_id: str, 
        search_request: GenerationSearchRequest
    ) -> GenerationSearchResponse:
        """Search within all files of a generation."""
        start_time = time.time()
        
        # Get generation directory
        generation_dir = await file_manager.get_generation_directory(generation_id)
        if not generation_dir or not generation_dir.exists():
            raise FileNotFoundError("Generation directory not found")
        
        # Get all searchable files
        searchable_files = self._get_searchable_files(
            generation_dir, 
            search_request.file_types
        )
        
        if len(searchable_files) > self.max_files_to_search:
            searchable_files = searchable_files[:self.max_files_to_search]
        
        # Perform search
        matches = []
        files_searched = 0
        
        # Compile regex if needed
        if search_request.regex:
            try:
                pattern = re.compile(
                    search_request.query,
                    0 if search_request.case_sensitive else re.IGNORECASE
                )
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        else:
            pattern = None
        
        for file_path in searchable_files:
            try:
                file_matches = self._search_file(
                    file_path, 
                    search_request, 
                    pattern,
                    generation_dir
                )
                matches.extend(file_matches)
                files_searched += 1
            except Exception:
                # Skip files that can't be read
                continue
        
        execution_time = time.time() - start_time
        
        return GenerationSearchResponse(
            matches=matches,
            total_matches=len(matches),
            files_searched=files_searched,
            query=search_request.query,
            execution_time=execution_time
        )
    
    def _get_searchable_files(self, generation_dir: Path, file_types: Optional[List[str]]) -> List[Path]:
        """Get list of files that can be searched."""
        searchable_files = []
        
        # Define searchable extensions
        text_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.cs',
            '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.sql',
            '.html', '.css', '.scss', '.sass', '.less', '.json', '.xml',
            '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.md', '.txt',
            '.sh', '.bat', '.ps1', '.dockerfile', '.gitignore', '.env'
        }
        
        for file_path in generation_dir.rglob('*'):
            if file_path.is_file():
                # Check file size
                if file_path.stat().st_size > self.max_file_size:
                    continue
                
                # Check extension
                if file_path.suffix.lower() not in text_extensions:
                    continue
                
                # Check file type filter
                if file_types:
                    file_ext = file_path.suffix.lower().lstrip('.')
                    if file_ext not in file_types:
                        continue
                
                searchable_files.append(file_path)
        
        return searchable_files
    
    def _search_file(
        self, 
        file_path: Path, 
        search_request: GenerationSearchRequest,
        pattern: Optional[re.Pattern],
        generation_dir: Path
    ) -> List[SearchMatch]:
        """Search within a single file."""
        matches = []
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except (UnicodeDecodeError, OSError):
            return matches
        
        # Get relative path
        relative_path = str(file_path.relative_to(generation_dir))
        
        # Search each line
        for line_num, line in enumerate(lines, 1):
            line_content = line.rstrip('\n\r')
            
            if pattern:
                # Regex search
                for match in pattern.finditer(line_content):
                    matches.append(self._create_search_match(
                        relative_path, line_num, line_content,
                        match.start(), match.end(),
                        lines, line_num - 1
                    ))
            else:
                # Simple text search
                search_text = search_request.query
                line_to_search = line_content if search_request.case_sensitive else line_content.lower()
                query_to_search = search_text if search_request.case_sensitive else search_text.lower()
                
                start_pos = 0
                while True:
                    pos = line_to_search.find(query_to_search, start_pos)
                    if pos == -1:
                        break
                    
                    matches.append(self._create_search_match(
                        relative_path, line_num, line_content,
                        pos, pos + len(search_text),
                        lines, line_num - 1
                    ))
                    start_pos = pos + 1
        
        return matches
    
    def _create_search_match(
        self,
        file_path: str,
        line_number: int,
        line_content: str,
        match_start: int,
        match_end: int,
        all_lines: List[str],
        line_index: int
    ) -> SearchMatch:
        """Create a search match object with context."""
        
        # Get context lines
        context_before = []
        context_after = []
        
        # Before context
        for i in range(max(0, line_index - self.context_lines), line_index):
            context_before.append(all_lines[i].rstrip('\n\r'))
        
        # After context
        for i in range(line_index + 1, min(len(all_lines), line_index + 1 + self.context_lines)):
            context_after.append(all_lines[i].rstrip('\n\r'))
        
        return SearchMatch(
            file_path=file_path,
            line_number=line_number,
            line_content=line_content,
            match_start=match_start,
            match_end=match_end,
            context_before=context_before,
            context_after=context_after
        )


class TemplateSearchService:
    """Service for searching and filtering templates."""
    
    def __init__(self):
        # Extended template database
        self.templates = [
            TemplateInfo(
                name="fastapi_basic",
                display_name="FastAPI Basic",
                description="Basic FastAPI project with authentication and database integration",
                tech_stack=["fastapi", "pydantic", "uvicorn", "sqlalchemy"],
                domain="api",
                complexity="low",
                features=["REST API", "Authentication", "Database ORM", "Auto Documentation"],
                estimated_files=15,
                estimated_setup_time="30 minutes"
            ),
            TemplateInfo(
                name="fastapi_advanced",
                display_name="FastAPI Advanced",
                description="Advanced FastAPI project with microservices architecture",
                tech_stack=["fastapi", "celery", "redis", "postgresql", "docker"],
                domain="enterprise",
                complexity="high",
                features=["Microservices", "Background Tasks", "Caching", "Containerization"],
                estimated_files=35,
                estimated_setup_time="2 hours"
            ),
            TemplateInfo(
                name="django_basic",
                display_name="Django Basic",
                description="Django project with admin interface and user management",
                tech_stack=["django", "postgresql", "bootstrap"],
                domain="web",
                complexity="medium",
                features=["Admin Interface", "User Management", "Templates", "ORM"],
                estimated_files=25,
                estimated_setup_time="45 minutes"
            ),
            TemplateInfo(
                name="react_app",
                display_name="React Application",
                description="Modern React application with TypeScript and state management",
                tech_stack=["react", "typescript", "redux", "tailwindcss"],
                domain="frontend",
                complexity="medium",
                features=["Component Library", "State Management", "Responsive Design", "TypeScript"],
                estimated_files=20,
                estimated_setup_time="45 minutes"
            ),
            TemplateInfo(
                name="nextjs_fullstack",
                display_name="Next.js Full Stack",
                description="Full-stack Next.js application with API routes and database",
                tech_stack=["nextjs", "typescript", "prisma", "tailwindcss"],
                domain="fullstack",
                complexity="high",
                features=["SSR/SSG", "API Routes", "Database Integration", "Authentication"],
                estimated_files=30,
                estimated_setup_time="90 minutes"
            ),
            TemplateInfo(
                name="flask_api",
                display_name="Flask REST API",
                description="Lightweight Flask REST API with JWT authentication",
                tech_stack=["flask", "flask-restful", "jwt", "sqlalchemy"],
                domain="api",
                complexity="low",
                features=["REST API", "JWT Auth", "Database ORM", "Lightweight"],
                estimated_files=12,
                estimated_setup_time="30 minutes"
            ),
            TemplateInfo(
                name="express_api",
                display_name="Express.js API",
                description="Node.js Express API with MongoDB and authentication",
                tech_stack=["expressjs", "mongodb", "jwt", "mongoose"],
                domain="api",
                complexity="medium",
                features=["REST API", "NoSQL Database", "Middleware", "Authentication"],
                estimated_files=18,
                estimated_setup_time="45 minutes"
            ),
            TemplateInfo(
                name="vue_spa",
                display_name="Vue.js SPA",
                description="Single Page Application built with Vue.js and Vuex",
                tech_stack=["vuejs", "vuex", "vue-router", "sass"],
                domain="frontend",
                complexity="medium",
                features=["SPA", "State Management", "Routing", "Component Library"],
                estimated_files=22,
                estimated_setup_time="45 minutes"
            ),
            TemplateInfo(
                name="ecommerce_full",
                display_name="E-commerce Platform",
                description="Complete e-commerce solution with payment integration",
                tech_stack=["fastapi", "react", "postgresql", "redis", "stripe"],
                domain="ecommerce",
                complexity="high",
                features=["Product Catalog", "Shopping Cart", "Payment Processing", "Order Management"],
                estimated_files=50,
                estimated_setup_time="3 hours"
            ),
            TemplateInfo(
                name="blog_cms",
                display_name="Blog CMS",
                description="Content Management System for blogs and articles",
                tech_stack=["django", "postgresql", "bootstrap", "ckeditor"],
                domain="content",
                complexity="medium",
                features=["Content Editor", "User Roles", "SEO Optimization", "Comments"],
                estimated_files=28,
                estimated_setup_time="60 minutes"
            )
        ]
    
    async def search_templates(self, search_request: TemplateSearchRequest) -> TemplateSearchResponse:
        """Search and filter templates based on criteria."""
        filtered_templates = self.templates.copy()
        filters_applied = {}
        
        # Apply query filter
        if search_request.query:
            query_lower = search_request.query.lower()
            filtered_templates = [
                template for template in filtered_templates
                if (query_lower in template.display_name.lower() or
                    query_lower in template.description.lower() or
                    any(query_lower in tech.lower() for tech in template.tech_stack) or
                    any(query_lower in feature.lower() for feature in template.features))
            ]
            filters_applied["query"] = search_request.query
        
        # Apply domain filter
        if search_request.domain:
            filtered_templates = [
                template for template in filtered_templates
                if template.domain == search_request.domain
            ]
            filters_applied["domain"] = search_request.domain
        
        # Apply tech stack filter
        if search_request.tech_stack:
            filtered_templates = [
                template for template in filtered_templates
                if any(tech.lower() in [t.lower() for t in template.tech_stack] 
                      for tech in search_request.tech_stack)
            ]
            filters_applied["tech_stack"] = search_request.tech_stack
        
        # Apply complexity filter
        if search_request.complexity:
            filtered_templates = [
                template for template in filtered_templates
                if template.complexity == search_request.complexity
            ]
            filters_applied["complexity"] = search_request.complexity
        
        # Apply features filter
        if search_request.features:
            filtered_templates = [
                template for template in filtered_templates
                if any(feature.lower() in [f.lower() for f in template.features]
                      for feature in search_request.features)
            ]
            filters_applied["features"] = search_request.features
        
        # Sort by relevance (complexity, then estimated files)
        complexity_order = {"low": 1, "medium": 2, "high": 3}
        filtered_templates.sort(key=lambda t: (complexity_order.get(t.complexity, 2), t.estimated_files))
        
        return TemplateSearchResponse(
            templates=filtered_templates,
            total=len(filtered_templates),
            query=search_request.query,
            filters_applied=filters_applied
        )


# Create singleton instances
generation_file_service = GenerationFileService()
generation_search_service = GenerationSearchService()
template_search_service = TemplateSearchService()