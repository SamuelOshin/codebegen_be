"""
Code quality assessment service.
Evaluates generated code for syntax, structure, security, and best practices.
"""

import ast
import re
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QualityLevel(str, Enum):
    """Quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class QualityIssue:
    """Represents a code quality issue."""
    file: str
    line: Optional[int]
    severity: str  # error, warning, info
    category: str  # syntax, security, style, structure
    message: str
    suggestion: Optional[str] = None


@dataclass
class QualityReport:
    """Code quality assessment report."""
    overall_score: float  # 0-100
    overall_level: QualityLevel
    total_files: int
    total_lines: int
    issues: List[QualityIssue]
    metrics: Dict[str, any]
    recommendations: List[str]


class QualityAssessor:
    """Assesses code quality for generated projects."""
    
    def __init__(self):
        self.max_complexity = 10
        self.max_function_length = 50
        self.max_file_length = 500
    
    async def assess_project(self, generation_id: str, files: Dict[str, str]) -> QualityReport:
        """
        Perform comprehensive quality assessment of a generated project.
        
        Args:
            generation_id: Unique identifier for the generation
            files: Dictionary mapping file paths to content
            
        Returns:
            QualityReport with scores, issues, and recommendations
        """
        try:
            issues = []
            metrics = {
                "syntax_errors": 0,
                "security_issues": 0,
                "style_violations": 0,
                "structure_issues": 0,
                "complexity_score": 0,
                "test_coverage": 0,
                "documentation_score": 0
            }
            
            total_lines = 0
            python_files = 0
            
            # Analyze each file
            for file_path, content in files.items():
                if not content.strip():
                    continue
                    
                lines = content.splitlines()
                total_lines += len(lines)
                
                # Python files get comprehensive analysis
                if file_path.endswith('.py'):
                    python_files += 1
                    file_issues = await self._analyze_python_file(file_path, content)
                    issues.extend(file_issues)
                    
                    # Update metrics
                    for issue in file_issues:
                        if issue.category == "syntax":
                            metrics["syntax_errors"] += 1
                        elif issue.category == "security":
                            metrics["security_issues"] += 1
                        elif issue.category == "style":
                            metrics["style_violations"] += 1
                        elif issue.category == "structure":
                            metrics["structure_issues"] += 1
                
                # Configuration files
                elif file_path.endswith(('.yaml', '.yml', '.json', '.toml')):
                    config_issues = await self._analyze_config_file(file_path, content)
                    issues.extend(config_issues)
                
                # Documentation files
                elif file_path.endswith('.md'):
                    doc_issues = await self._analyze_documentation(file_path, content)
                    issues.extend(doc_issues)
            
            # Calculate complexity score
            if python_files > 0:
                metrics["complexity_score"] = await self._calculate_complexity(files)
                metrics["documentation_score"] = await self._calculate_documentation_score(files)
                metrics["test_coverage"] = await self._estimate_test_coverage(files)
            
            # Calculate overall score
            overall_score = await self._calculate_overall_score(metrics, issues, total_lines)
            overall_level = self._get_quality_level(overall_score)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(metrics, issues)
            
            return QualityReport(
                overall_score=overall_score,
                overall_level=overall_level,
                total_files=len(files),
                total_lines=total_lines,
                issues=issues,
                metrics=metrics,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error assessing project quality: {e}")
            return QualityReport(
                overall_score=0.0,
                overall_level=QualityLevel.POOR,
                total_files=0,
                total_lines=0,
                issues=[],
                metrics={},
                recommendations=["Error occurred during quality assessment"]
            )
    
    async def _analyze_python_file(self, file_path: str, content: str) -> List[QualityIssue]:
        """Analyze a Python file for quality issues."""
        issues = []
        
        try:
            # Parse AST for syntax checking
            tree = ast.parse(content)
            
            # Check for various issues
            issues.extend(self._check_syntax_issues(file_path, content, tree))
            issues.extend(self._check_security_issues(file_path, content))
            issues.extend(self._check_style_issues(file_path, content))
            issues.extend(self._check_structure_issues(file_path, content, tree))
            
        except SyntaxError as e:
            issues.append(QualityIssue(
                file=file_path,
                line=e.lineno,
                severity="error",
                category="syntax",
                message=f"Syntax error: {e.msg}",
                suggestion="Fix the syntax error before proceeding"
            ))
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
        
        return issues
    
    def _check_syntax_issues(self, file_path: str, content: str, tree: ast.AST) -> List[QualityIssue]:
        """Check for syntax-related issues."""
        issues = []
        lines = content.splitlines()
        
        # Check for common syntax patterns
        for i, line in enumerate(lines, 1):
            # Trailing whitespace
            if line.endswith(' ') or line.endswith('\t'):
                issues.append(QualityIssue(
                    file=file_path,
                    line=i,
                    severity="warning",
                    category="style",
                    message="Trailing whitespace",
                    suggestion="Remove trailing whitespace"
                ))
            
            # Long lines
            if len(line) > 88:
                issues.append(QualityIssue(
                    file=file_path,
                    line=i,
                    severity="warning",
                    category="style",
                    message="Line too long",
                    suggestion="Break long lines for better readability"
                ))
        
        return issues
    
    def _check_security_issues(self, file_path: str, content: str) -> List[QualityIssue]:
        """Check for security-related issues."""
        issues = []
        lines = content.splitlines()
        
        security_patterns = [
            (r'exec\s*\(', "Use of exec() function"),
            (r'eval\s*\(', "Use of eval() function"),
            (r'__import__\s*\(', "Use of __import__() function"),
            (r'pickle\.loads?\s*\(', "Use of pickle.load/loads"),
            (r'subprocess\.call\s*\(.*shell\s*=\s*True', "Shell injection risk"),
            (r'sql\s*=\s*["\'].*%.*["\']', "Potential SQL injection"),
            (r'password\s*=\s*["\'][^"\']*["\']', "Hardcoded password"),
            (r'secret\s*=\s*["\'][^"\']*["\']', "Hardcoded secret"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, message in security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(QualityIssue(
                        file=file_path,
                        line=i,
                        severity="error",
                        category="security",
                        message=message,
                        suggestion="Review for security implications"
                    ))
        
        return issues
    
    def _check_style_issues(self, file_path: str, content: str) -> List[QualityIssue]:
        """Check for style-related issues."""
        issues = []
        lines = content.splitlines()
        
        # Check imports organization
        import_lines = [i for i, line in enumerate(lines) if line.strip().startswith(('import ', 'from '))]
        
        if import_lines:
            # Check for imports not at the top
            first_non_comment = None
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and not stripped.startswith('"""'):
                    first_non_comment = i
                    break
            
            if first_non_comment is not None and import_lines[0] > first_non_comment:
                issues.append(QualityIssue(
                    file=file_path,
                    line=import_lines[0] + 1,
                    severity="warning",
                    category="style",
                    message="Imports should be at the top of the file",
                    suggestion="Move imports to the beginning of the file"
                ))
        
        # Check for missing docstrings in functions and classes
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    issues.append(QualityIssue(
                        file=file_path,
                        line=node.lineno,
                        severity="warning",
                        category="structure",
                        message=f"Missing docstring for {node.name}",
                        suggestion="Add descriptive docstring"
                    ))
        
        return issues
    
    def _check_structure_issues(self, file_path: str, content: str, tree: ast.AST) -> List[QualityIssue]:
        """Check for structural issues."""
        issues = []
        
        # Check function complexity and length
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Calculate cyclomatic complexity (simplified)
                complexity = self._calculate_cyclomatic_complexity(node)
                if complexity > self.max_complexity:
                    issues.append(QualityIssue(
                        file=file_path,
                        line=node.lineno,
                        severity="warning",
                        category="structure",
                        message=f"Function '{node.name}' has high complexity ({complexity})",
                        suggestion="Consider breaking down into smaller functions"
                    ))
                
                # Check function length
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    length = node.end_lineno - node.lineno
                    if length > self.max_function_length:
                        issues.append(QualityIssue(
                            file=file_path,
                            line=node.lineno,
                            severity="warning",
                            category="structure",
                            message=f"Function '{node.name}' is too long ({length} lines)",
                            suggestion="Consider breaking down into smaller functions"
                        ))
        
        return issues
    
    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate simplified cyclomatic complexity."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Add 1 for each decision point
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    async def _analyze_config_file(self, file_path: str, content: str) -> List[QualityIssue]:
        """Analyze configuration files."""
        issues = []
        
        # Check for sensitive data in config files
        sensitive_patterns = [
            r'password\s*[:=]\s*["\'][^"\']+["\']',
            r'secret\s*[:=]\s*["\'][^"\']+["\']',
            r'key\s*[:=]\s*["\'][^"\']+["\']',
            r'token\s*[:=]\s*["\'][^"\']+["\']'
        ]
        
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            for pattern in sensitive_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(QualityIssue(
                        file=file_path,
                        line=i,
                        severity="warning",
                        category="security",
                        message="Potential sensitive data in config file",
                        suggestion="Use environment variables for sensitive data"
                    ))
        
        return issues
    
    async def _analyze_documentation(self, file_path: str, content: str) -> List[QualityIssue]:
        """Analyze documentation files."""
        issues = []
        
        # Check for basic README structure
        if file_path.lower() == 'readme.md':
            required_sections = ['installation', 'usage', 'api']
            content_lower = content.lower()
            
            for section in required_sections:
                if section not in content_lower:
                    issues.append(QualityIssue(
                        file=file_path,
                        line=None,
                        severity="info",
                        category="documentation",
                        message=f"Missing {section} section",
                        suggestion=f"Add {section} section to README"
                    ))
        
        return issues
    
    async def _calculate_complexity(self, files: Dict[str, str]) -> float:
        """Calculate overall project complexity score."""
        total_complexity = 0
        function_count = 0
        
        for file_path, content in files.items():
            if not file_path.endswith('.py'):
                continue
                
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        function_count += 1
                        total_complexity += self._calculate_cyclomatic_complexity(node)
            except:
                continue
        
        return total_complexity / max(function_count, 1)
    
    async def _calculate_documentation_score(self, files: Dict[str, str]) -> float:
        """Calculate documentation coverage score."""
        documented_items = 0
        total_items = 0
        
        for file_path, content in files.items():
            if not file_path.endswith('.py'):
                continue
                
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        total_items += 1
                        if ast.get_docstring(node):
                            documented_items += 1
            except:
                continue
        
        return (documented_items / max(total_items, 1)) * 100
    
    async def _estimate_test_coverage(self, files: Dict[str, str]) -> float:
        """Estimate test coverage based on test files."""
        test_files = len([f for f in files.keys() if 'test' in f.lower()])
        total_python_files = len([f for f in files.keys() if f.endswith('.py')])
        
        # Simple heuristic: if we have test files, assume some coverage
        if test_files > 0:
            return min((test_files / max(total_python_files, 1)) * 100, 85)
        return 0
    
    async def _calculate_overall_score(
        self, 
        metrics: Dict[str, any], 
        issues: List[QualityIssue], 
        total_lines: int
    ) -> float:
        """Calculate overall quality score."""
        base_score = 100.0
        
        # Deduct points for issues
        for issue in issues:
            if issue.severity == "error":
                base_score -= 10
            elif issue.severity == "warning":
                base_score -= 3
            elif issue.severity == "info":
                base_score -= 1
        
        # Complexity penalty
        if metrics.get("complexity_score", 0) > self.max_complexity:
            base_score -= 15
        
        # Documentation bonus
        doc_score = metrics.get("documentation_score", 0)
        if doc_score > 80:
            base_score += 5
        elif doc_score < 30:
            base_score -= 10
        
        # Test coverage bonus
        test_coverage = metrics.get("test_coverage", 0)
        if test_coverage > 70:
            base_score += 10
        elif test_coverage == 0:
            base_score -= 15
        
        return max(0, min(100, base_score))
    
    def _get_quality_level(self, score: float) -> QualityLevel:
        """Convert score to quality level."""
        if score >= 85:
            return QualityLevel.EXCELLENT
        elif score >= 70:
            return QualityLevel.GOOD
        elif score >= 50:
            return QualityLevel.FAIR
        else:
            return QualityLevel.POOR
    
    async def _generate_recommendations(
        self, 
        metrics: Dict[str, any], 
        issues: List[QualityIssue]
    ) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        # Security recommendations
        security_issues = [i for i in issues if i.category == "security"]
        if security_issues:
            recommendations.append("Address security vulnerabilities before deployment")
        
        # Documentation recommendations
        doc_score = metrics.get("documentation_score", 0)
        if doc_score < 50:
            recommendations.append("Add comprehensive docstrings to functions and classes")
        
        # Test coverage recommendations
        test_coverage = metrics.get("test_coverage", 0)
        if test_coverage < 30:
            recommendations.append("Implement unit tests for better code reliability")
        
        # Complexity recommendations
        complexity = metrics.get("complexity_score", 0)
        if complexity > self.max_complexity:
            recommendations.append("Refactor complex functions into smaller, focused functions")
        
        # Style recommendations
        style_issues = [i for i in issues if i.category == "style"]
        if len(style_issues) > 10:
            recommendations.append("Run a code formatter (black, autopep8) to improve code style")
        
        # Structure recommendations
        structure_issues = [i for i in issues if i.category == "structure"]
        if structure_issues:
            recommendations.append("Improve code organization and structure")
        
        if not recommendations:
            recommendations.append("Code quality looks good! Consider adding more tests and documentation.")
        
        return recommendations


# Global instance
quality_assessor = QualityAssessor()
