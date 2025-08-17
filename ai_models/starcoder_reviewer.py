"""
Starcoder2-15B model wrapper for code review and security analysis.
Handles code quality assessment, security scanning, and improvement suggestions.
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional
import ast

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: Transformers/PyTorch not available. Code review will be limited.")

from app.core.config import settings


class StarcoderReviewer:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model: Optional[AutoModelForCausalLM] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    async def load(self):
        """Load Starcoder model for code review"""
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
        
        print(f"Loaded Starcoder reviewer model: {self.model_path}")

    async def review_code(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Perform comprehensive code review on generated files"""
        
        # Static analysis first
        static_analysis = self._perform_static_analysis(files)
        
        # AI-powered review
        ai_review = await self._ai_code_review(files)
        
        # Combine results
        combined_review = self._combine_reviews(static_analysis, ai_review)
        
        # Calculate scores
        scores = self._calculate_scores(combined_review, files)
        
        return {
            "issues": combined_review.get("issues", []),
            "suggestions": combined_review.get("suggestions", []),
            "security_score": scores["security"],
            "maintainability_score": scores["maintainability"],
            "performance_score": scores["performance"],
            "overall_score": scores["overall"],
            "metrics": {
                "total_lines": sum(len(content.split('\n')) for content in files.values()),
                "total_files": len(files),
                "complexity_score": scores.get("complexity", 0.8)
            }
        }

    def _perform_static_analysis(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Perform static code analysis without AI"""
        issues = []
        suggestions = []
        
        for file_path, content in files.items():
            if file_path.endswith('.py'):
                # Python-specific analysis
                py_issues, py_suggestions = self._analyze_python_file(file_path, content)
                issues.extend(py_issues)
                suggestions.extend(py_suggestions)
            elif file_path.endswith(('.yml', '.yaml')):
                # YAML analysis
                yaml_issues = self._analyze_yaml_file(file_path, content)
                issues.extend(yaml_issues)
            elif file_path == 'Dockerfile':
                # Dockerfile analysis
                docker_issues = self._analyze_dockerfile(file_path, content)
                issues.extend(docker_issues)
        
        return {
            "issues": issues,
            "suggestions": suggestions
        }

    def _analyze_python_file(self, file_path: str, content: str) -> tuple[List[Dict], List[Dict]]:
        """Analyze Python file for common issues"""
        issues = []
        suggestions = []
        lines = content.split('\n')
        
        try:
            # Parse AST for syntax validation
            ast.parse(content)
        except SyntaxError as e:
            issues.append({
                "file": file_path,
                "line": e.lineno or 0,
                "severity": "error",
                "category": "syntax",
                "message": f"Syntax error: {e.msg}",
                "code": "SYNTAX_ERROR"
            })
            return issues, suggestions
        
        # Check for common issues
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Security issues
            if 'eval(' in line or 'exec(' in line:
                issues.append({
                    "file": file_path,
                    "line": i,
                    "severity": "high",
                    "category": "security",
                    "message": "Avoid using eval() or exec() - potential security risk",
                    "code": "DANGEROUS_FUNCTION"
                })
            
            if 'password' in line.lower() and ('=' in line or ':' in line):
                if not any(secure in line.lower() for secure in ['hash', 'encrypt', 'secret', 'env']):
                    issues.append({
                        "file": file_path,
                        "line": i,
                        "severity": "medium",
                        "category": "security",
                        "message": "Potential hardcoded password - use environment variables",
                        "code": "HARDCODED_SECRET"
                    })
            
            # Code quality issues
            if len(line) > 88:  # PEP 8 line length
                issues.append({
                    "file": file_path,
                    "line": i,
                    "severity": "low",
                    "category": "style",
                    "message": f"Line too long ({len(line)} > 88 characters)",
                    "code": "LINE_TOO_LONG"
                })
            
            # Missing docstrings for functions/classes
            if (line_stripped.startswith('def ') or line_stripped.startswith('class ')) and ':' in line:
                next_line_idx = i
                has_docstring = False
                while next_line_idx < len(lines):
                    next_line = lines[next_line_idx].strip()
                    if next_line.startswith('"""') or next_line.startswith("'''"):
                        has_docstring = True
                        break
                    elif next_line and not next_line.startswith('#'):
                        break
                    next_line_idx += 1
                
                if not has_docstring:
                    suggestions.append({
                        "file": file_path,
                        "line": i,
                        "category": "documentation",
                        "message": "Consider adding a docstring to document this function/class",
                        "code": "MISSING_DOCSTRING"
                    })
        
        # FastAPI-specific suggestions
        if 'fastapi' in content.lower():
            if '@app.get' in content and 'response_model' not in content:
                suggestions.append({
                    "file": file_path,
                    "line": 0,
                    "category": "api_design",
                    "message": "Consider adding response_model to endpoints for better API documentation",
                    "code": "MISSING_RESPONSE_MODEL"
                })
            
            if 'HTTPException' not in content and ('get' in content or 'post' in content):
                suggestions.append({
                    "file": file_path,
                    "line": 0,
                    "category": "error_handling",
                    "message": "Consider adding proper error handling with HTTPException",
                    "code": "MISSING_ERROR_HANDLING"
                })
        
        return issues, suggestions

    def _analyze_yaml_file(self, file_path: str, content: str) -> List[Dict]:
        """Analyze YAML files for common issues"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for tabs (YAML should use spaces)
            if '\t' in line:
                issues.append({
                    "file": file_path,
                    "line": i,
                    "severity": "medium",
                    "category": "format",
                    "message": "YAML files should use spaces, not tabs",
                    "code": "YAML_TABS"
                })
        
        return issues

    def _analyze_dockerfile(self, file_path: str, content: str) -> List[Dict]:
        """Analyze Dockerfile for best practices"""
        issues = []
        lines = content.split('\n')
        
        has_user = False
        has_healthcheck = False
        
        for i, line in enumerate(lines, 1):
            line_upper = line.upper().strip()
            
            if line_upper.startswith('USER '):
                has_user = True
            
            if line_upper.startswith('HEALTHCHECK '):
                has_healthcheck = True
            
            if line_upper.startswith('RUN apt-get update') and 'apt-get clean' not in content:
                issues.append({
                    "file": file_path,
                    "line": i,
                    "severity": "medium",
                    "category": "optimization",
                    "message": "Consider cleaning apt cache after installation to reduce image size",
                    "code": "DOCKER_APT_CLEAN"
                })
        
        if not has_user:
            issues.append({
                "file": file_path,
                "line": 0,
                "severity": "high",
                "category": "security",
                "message": "Consider adding USER instruction to avoid running as root",
                "code": "DOCKER_ROOT_USER"
            })
        
        if not has_healthcheck:
            issues.append({
                "file": file_path,
                "line": 0,
                "severity": "low",
                "category": "monitoring",
                "message": "Consider adding HEALTHCHECK instruction",
                "code": "DOCKER_MISSING_HEALTHCHECK"
            })
        
        return issues

    async def _ai_code_review(self, files: Dict[str, str]) -> Dict[str, Any]:
        """AI-powered code review using Starcoder model"""
        
        # Prepare code for review
        code_summary = self._prepare_code_for_review(files)
        
        # Format prompt for AI review
        review_prompt = self._format_review_prompt(code_summary)
        
        # Generate review
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, self._generate_review, review_prompt)
        
        # Parse review output
        review_result = self._parse_review_output(output)
        
        return review_result

    def _prepare_code_for_review(self, files: Dict[str, str]) -> str:
        """Prepare code summary for AI review"""
        summary_parts = []
        
        # Prioritize important files
        priority_files = ['main.py', 'app.py', 'models.py', 'schemas.py', 'routers.py']
        
        for file_path, content in files.items():
            # Include full content for small files, summary for large files
            if len(content) < 2000:
                summary_parts.append(f"=== {file_path} ===\n{content}\n")
            else:
                # Include just function/class signatures for large files
                lines = content.split('\n')
                important_lines = []
                for line in lines[:50]:  # First 50 lines
                    if any(keyword in line for keyword in ['def ', 'class ', 'import ', 'from ']):
                        important_lines.append(line)
                
                summary_parts.append(f"=== {file_path} (summary) ===\n" + '\n'.join(important_lines) + "\n")
        
        return '\n'.join(summary_parts)

    def _format_review_prompt(self, code_summary: str) -> str:
        """Format prompt for AI code review"""
        
        system_prompt = """You are an expert code reviewer with deep knowledge of Python, FastAPI, security, and software engineering best practices.

Review the provided code and identify:
1. Security vulnerabilities
2. Performance issues
3. Code quality problems
4. Best practice violations
5. Architecture concerns

Output your review as JSON with:
{
  "issues": [
    {"file": "filename", "line": 0, "severity": "high|medium|low", "category": "security|performance|quality", "message": "Description", "code": "ISSUE_CODE"}
  ],
  "suggestions": [
    {"category": "security|performance|architecture", "message": "Improvement suggestion", "priority": "high|medium|low"}
  ]
}"""

        user_prompt = f"""### Code to Review:
{code_summary}

### Review Focus:
- FastAPI best practices
- Python security patterns
- Database query optimization
- Error handling completeness
- API design quality
- Code maintainability

Provide specific, actionable feedback in JSON format:"""

        return f"{system_prompt}\n\n{user_prompt}"

    def _generate_review(self, prompt: str) -> str:
        """Synchronous review generation"""
        inputs = self.tokenizer(
            prompt, 
            return_tensors="pt", 
            truncation=True, 
            max_length=4096
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1500,
                temperature=0.1,
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

    def _parse_review_output(self, output: str) -> Dict[str, Any]:
        """Parse AI review output"""
        try:
            # Find JSON in the output
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                review = json.loads(json_str)
                return review
            else:
                return {"issues": [], "suggestions": []}
                
        except json.JSONDecodeError:
            # Fallback: extract issues from text
            return self._extract_review_from_text(output)

    def _extract_review_from_text(self, output: str) -> Dict[str, Any]:
        """Fallback extraction from natural language review"""
        issues = []
        suggestions = []
        
        # Look for issue patterns
        issue_patterns = [
            r"security.*(?:issue|problem|vulnerability)",
            r"performance.*(?:issue|problem|concern)",
            r"error.*(?:handling|missing)"
        ]
        
        lines = output.split('\n')
        for line in lines:
            line_lower = line.lower()
            for pattern in issue_patterns:
                if re.search(pattern, line_lower):
                    issues.append({
                        "file": "general",
                        "line": 0,
                        "severity": "medium",
                        "category": "general",
                        "message": line.strip(),
                        "code": "AI_DETECTED"
                    })
                    break
        
        return {"issues": issues, "suggestions": suggestions}

    def _combine_reviews(self, static_analysis: Dict[str, Any], ai_review: Dict[str, Any]) -> Dict[str, Any]:
        """Combine static analysis and AI review results"""
        combined_issues = static_analysis.get("issues", []) + ai_review.get("issues", [])
        combined_suggestions = static_analysis.get("suggestions", []) + ai_review.get("suggestions", [])
        
        # Remove duplicates
        unique_issues = []
        seen_issues = set()
        
        for issue in combined_issues:
            issue_key = (issue.get("file", ""), issue.get("line", 0), issue.get("message", ""))
            if issue_key not in seen_issues:
                unique_issues.append(issue)
                seen_issues.add(issue_key)
        
        return {
            "issues": unique_issues,
            "suggestions": combined_suggestions
        }

    def _calculate_scores(self, review: Dict[str, Any], files: Dict[str, str]) -> Dict[str, float]:
        """Calculate quality scores based on review results"""
        issues = review.get("issues", [])
        
        # Count issues by severity and category
        high_issues = len([i for i in issues if i.get("severity") == "high"])
        medium_issues = len([i for i in issues if i.get("severity") == "medium"])
        low_issues = len([i for i in issues if i.get("severity") == "low"])
        
        security_issues = len([i for i in issues if i.get("category") == "security"])
        performance_issues = len([i for i in issues if i.get("category") == "performance"])
        quality_issues = len([i for i in issues if i.get("category") in ["style", "quality", "documentation"]])
        
        # Base scores
        security_score = max(0.0, 1.0 - (high_issues * 0.3 + security_issues * 0.2))
        performance_score = max(0.0, 1.0 - (performance_issues * 0.25))
        maintainability_score = max(0.0, 1.0 - (quality_issues * 0.1 + medium_issues * 0.15))
        
        # Overall score
        overall_score = (security_score * 0.4 + performance_score * 0.3 + maintainability_score * 0.3)
        
        return {
            "security": round(security_score, 2),
            "performance": round(performance_score, 2),
            "maintainability": round(maintainability_score, 2),
            "overall": round(overall_score, 2),
            "complexity": 0.8  # Placeholder for complexity analysis
        }

    async def cleanup(self):
        """Cleanup model resources"""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        torch.cuda.empty_cache()
        print("Starcoder reviewer cleanup completed")
