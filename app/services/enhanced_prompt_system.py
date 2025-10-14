"""
Enhanced Prompt Engineering System for CodeBEGen

Implements Phase 2 of the Two-Week Validation Test:
- Multi-model prompt optimization
- Context-aware generation using user history
- Prompt chain refinement
- User pattern analysis and similarity matching

Target: 25-35% improvement in generation quality
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import re
from collections import Counter
from abc import ABC, abstractmethod

from app.models.project import Project
from app.models.user import User
from app.models.generation import Generation
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.repositories.generation_repository import GenerationRepository


@dataclass
class UserContext:
    """Comprehensive user context for prompt enhancement"""
    user_id: str
    successful_projects: List[Dict[str, Any]] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    common_modifications: List[str] = field(default_factory=list)
    tech_stack_history: List[str] = field(default_factory=list)
    architecture_style: str = "microservices"
    complexity_preference: str = "moderate"
    frequent_features: List[str] = field(default_factory=list)
    domain_expertise: List[str] = field(default_factory=list)
    generation_patterns: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptContext:
    """Context for prompt generation and enhancement"""
    original_prompt: str
    user_context: UserContext
    similar_projects: List[Dict[str, Any]] = field(default_factory=list)
    domain_context: Dict[str, Any] = field(default_factory=dict)
    technical_constraints: List[str] = field(default_factory=list)
    business_requirements: List[str] = field(default_factory=list)
    suggested_features: List[str] = field(default_factory=list)


class BasePromptTemplate(ABC):
    """Abstract base class for prompt templates"""
    
    @abstractmethod
    def generate_prompt(self, context: PromptContext) -> str:
        """Generate enhanced prompt from context"""
        pass
    
    @abstractmethod
    def get_template_type(self) -> str:
        """Return the type of this template"""
        pass


class IntentClarificationTemplate(BasePromptTemplate):
    """Template for clarifying user intent and extracting requirements"""
    
    def generate_prompt(self, context: PromptContext) -> str:
        """Generate intent clarification prompt"""
        
        user_patterns = self._format_user_patterns(context.user_context)
        similar_context = self._format_similar_projects(context.similar_projects)
        
        return f"""
You are an expert system architect analyzing a backend development request.

ORIGINAL REQUEST: {context.original_prompt}

USER CONTEXT:
{user_patterns}

SIMILAR SUCCESSFUL PROJECTS:
{similar_context}

TASK: Analyze this request and extract clear, specific requirements.

Please provide a structured analysis:

1. CORE ENTITIES AND RELATIONSHIPS:
   - What are the main data models needed?
   - How do they relate to each other?
   - What are the key attributes for each entity?

2. REQUIRED FUNCTIONALITY:
   - What CRUD operations are needed?
   - What business logic must be implemented?
   - What integrations are required?

3. TECHNICAL CONSTRAINTS:
   - What technology stack is implied or preferred?
   - What performance requirements exist?
   - What scalability considerations apply?

4. AUTHENTICATION & SECURITY:
   - What authentication method is appropriate?
   - What authorization levels are needed?
   - What security measures are required?

5. BUSINESS LOGIC REQUIREMENTS:
   - What workflows need to be supported?
   - What validation rules apply?
   - What business rules must be enforced?

6. INTEGRATION NEEDS:
   - What external services need integration?
   - What APIs need to be consumed or provided?
   - What data import/export is required?

Based on the user's history, I recommend focusing on: {', '.join(context.user_context.frequent_features)}

Please provide specific, implementable requirements that avoid ambiguity.
"""
    
    def get_template_type(self) -> str:
        return "intent_clarification"
    
    def _format_user_patterns(self, user_context: UserContext) -> str:
        """Format user patterns for prompt inclusion"""
        patterns = []
        
        if user_context.architecture_style:
            patterns.append(f"- Preferred Architecture: {user_context.architecture_style}")
        
        if user_context.tech_stack_history:
            tech_stacks = Counter(user_context.tech_stack_history).most_common(3)
            patterns.append(f"- Common Tech Stacks: {', '.join([stack for stack, _ in tech_stacks])}")
        
        if user_context.frequent_features:
            patterns.append(f"- Frequently Used Features: {', '.join(user_context.frequent_features)}")
        
        if user_context.complexity_preference:
            patterns.append(f"- Complexity Preference: {user_context.complexity_preference}")
        
        if user_context.domain_expertise:
            patterns.append(f"- Domain Experience: {', '.join(user_context.domain_expertise)}")
        
        return "\n".join(patterns) if patterns else "- No previous project history available"
    
    def _format_similar_projects(self, similar_projects: List[Dict[str, Any]]) -> str:
        """Format similar projects for context"""
        if not similar_projects:
            return "- No similar projects found"
        
        formatted = []
        for i, project in enumerate(similar_projects[:3], 1):
            formatted.append(f"- Project {i}: {project.get('description', 'N/A')} "
                           f"(Features: {', '.join(project.get('features', []))})")
        
        return "\n".join(formatted)


class ArchitecturePlanningTemplate(BasePromptTemplate):
    """Template for designing system architecture"""
    
    def generate_prompt(self, context: PromptContext) -> str:
        """Generate architecture planning prompt"""
        
        return f"""
You are a senior software architect designing a FastAPI backend system.

CLARIFIED REQUIREMENTS: {context.original_prompt}

USER PREFERENCES:
- Architecture Style: {context.user_context.architecture_style}
- Complexity Level: {context.user_context.complexity_preference}
- Preferred Features: {', '.join(context.user_context.frequent_features)}

DESIGN TASK: Create a comprehensive system architecture.

Please provide a detailed architecture plan:

1. DATABASE SCHEMA:
   - Define all tables/collections with fields and types
   - Specify relationships (foreign keys, indexes)
   - Include any constraints and validations
   - Consider scalability and performance

2. API ENDPOINTS:
   - List all RESTful endpoints needed
   - Specify HTTP methods, paths, and purposes
   - Define request/response schemas
   - Include authentication requirements

3. SERVICE LAYER DESIGN:
   - Identify business logic services
   - Define service responsibilities
   - Specify inter-service communication
   - Include error handling patterns

4. AUTHENTICATION STRATEGY:
   - Choose appropriate auth method (JWT, OAuth, etc.)
   - Define user roles and permissions
   - Specify protected vs public endpoints
   - Include security best practices

5. FILE STRUCTURE:
   - Organize code into logical modules
   - Define clear separation of concerns
   - Follow FastAPI best practices
   - Include configuration management

6. EXTERNAL INTEGRATIONS:
   - Identify required third-party services
   - Define integration patterns
   - Include error handling and fallbacks
   - Specify configuration requirements

7. CACHING STRATEGY:
   - Identify cacheable data and operations
   - Choose appropriate caching layers
   - Define cache invalidation strategies
   - Include performance considerations

Focus on production-ready, maintainable architecture that follows the user's established patterns.
Emphasize security, scalability, and code organization.
"""
    
    def get_template_type(self) -> str:
        return "architecture_planning"


class ImplementationGenerationTemplate(BasePromptTemplate):
    """Template for generating actual implementation code"""
    
    def generate_prompt(self, context: PromptContext) -> str:
        """Generate implementation prompt"""
        
        feature_guidance = self._generate_feature_guidance(context.user_context.frequent_features)
        
        return f"""
You are an expert FastAPI developer implementing a production-ready backend system.

ARCHITECTURE SPECIFICATION: {context.original_prompt}

USER CODING PATTERNS:
- Common Modifications: {', '.join(context.user_context.common_modifications)}
- Preferred Tech Stack: {', '.join(context.user_context.tech_stack_history[-3:])}
- Architecture Style: {context.user_context.architecture_style}

IMPLEMENTATION REQUIREMENTS:

1. CODE QUALITY STANDARDS:
   - Follow PEP 8 style guidelines
   - Include comprehensive docstrings
   - Add type hints throughout
   - Implement proper error handling
   - Include logging for debugging

2. SECURITY IMPLEMENTATION:
   - Input validation for all endpoints
   - SQL injection prevention
   - Authentication middleware
   - Rate limiting where appropriate
   - Secure password handling

3. PERFORMANCE OPTIMIZATION:
   - Database query optimization
   - Async/await where beneficial
   - Connection pooling
   - Caching implementation
   - Efficient data serialization

4. TESTING INFRASTRUCTURE:
   - Unit tests for business logic
   - Integration tests for APIs
   - Test fixtures and factories
   - Mocking external dependencies
   - Coverage reporting setup

5. PRODUCTION READINESS:
   - Environment configuration
   - Docker containerization
   - Health check endpoints
   - Monitoring and metrics
   - Error tracking integration

{feature_guidance}

DELIVERABLE: Complete, deployable FastAPI application with:
- All source code files
- Requirements.txt with exact versions
- Environment configuration templates
- Basic documentation
- Docker setup
- Unit tests for core functionality

Ensure the code follows the user's established patterns and preferences.
Generate clean, maintainable code that a senior developer would approve.
"""
    
    def get_template_type(self) -> str:
        return "implementation_generation"
    
    def _generate_feature_guidance(self, frequent_features: List[str]) -> str:
        """Generate specific guidance based on user's frequent features"""
        guidance = ["6. FEATURE-SPECIFIC REQUIREMENTS:"]
        
        feature_requirements = {
            "authentication": "- Implement JWT-based authentication with refresh tokens\n"
                            "- Include user registration, login, and profile management\n"
                            "- Add role-based access control (RBAC)",
            
            "file_upload": "- Implement secure file upload with validation\n"
                          "- Support multiple file types with size limits\n"
                          "- Include file metadata and storage management",
            
            "payments": "- Integrate with Stripe for payment processing\n"
                       "- Implement subscription and one-time payment flows\n"
                       "- Include webhook handling for payment events",
            
            "caching": "- Implement Redis-based caching with TTL\n"
                      "- Add cache invalidation strategies\n"
                      "- Include performance monitoring for cache hits",
            
            "search": "- Implement full-text search capabilities\n"
                     "- Add filtering and sorting options\n"
                     "- Include search analytics and optimization",
            
            "real_time": "- Implement WebSocket connections for real-time updates\n"
                        "- Add event broadcasting and subscription management\n"
                        "- Include connection state management",
            
            "admin_dashboard": "- Create admin-only endpoints for system management\n"
                              "- Include user management and analytics\n"
                              "- Add system monitoring and health checks"
        }
        
        for feature in frequent_features:
            if feature in feature_requirements:
                guidance.append(feature_requirements[feature])
        
        if len(guidance) == 1:  # Only header added
            guidance.append("- Follow standard FastAPI patterns and best practices")
        
        return "\n".join(guidance)


class PromptChain:
    """Multi-stage prompt refinement system"""
    
    def __init__(self):
        self.templates = {
            "intent_clarification": IntentClarificationTemplate(),
            "architecture_planning": ArchitecturePlanningTemplate(),
            "implementation_generation": ImplementationGenerationTemplate()
        }
    
    def process_prompt_chain(
        self, 
        raw_prompt: str, 
        user_context: UserContext,
        similar_projects: List[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Process prompt through the entire chain"""
        
        similar_projects = similar_projects or []
        context = PromptContext(
            original_prompt=raw_prompt,
            user_context=user_context,
            similar_projects=similar_projects
        )
        
        results = {}
        
        # Stage 1: Intent Clarification
        intent_prompt = self.templates["intent_clarification"].generate_prompt(context)
        results["intent_clarification"] = intent_prompt
        
        # For now, we'll simulate the response - in real implementation,
        # this would call the AI model and use the response for the next stage
        clarified_intent = f"Clarified requirements based on: {raw_prompt}"
        
        # Stage 2: Architecture Planning
        arch_context = PromptContext(
            original_prompt=clarified_intent,
            user_context=user_context,
            similar_projects=similar_projects
        )
        architecture_prompt = self.templates["architecture_planning"].generate_prompt(arch_context)
        results["architecture_planning"] = architecture_prompt
        
        # Simulate architecture response
        architecture_spec = f"Architecture specification for: {clarified_intent}"
        
        # Stage 3: Implementation Generation
        impl_context = PromptContext(
            original_prompt=architecture_spec,
            user_context=user_context,
            similar_projects=similar_projects
        )
        implementation_prompt = self.templates["implementation_generation"].generate_prompt(impl_context)
        results["implementation_generation"] = implementation_prompt
        
        return results


class UserPatternAnalyzer:
    """Analyzes user patterns and preferences from project history"""
    
    def __init__(
        self, 
        project_repository: ProjectRepository,
        user_repository: UserRepository,
        generation_repository: GenerationRepository
    ):
        self.project_repo = project_repository
        self.user_repo = user_repository
        self.generation_repo = generation_repository
    
    def analyze_user_patterns(self, user_id: str) -> UserContext:
        """Analyze user's historical patterns and preferences"""
        
        # Get user's project history
        user_projects = self.project_repo.get_by_user_id(user_id)
        successful_projects = [
            project for project in user_projects 
            if project.status == "completed"
        ]
        
        # Analyze patterns
        tech_stacks = self._extract_tech_stacks(successful_projects)
        features = self._extract_common_features(successful_projects)
        modifications = self._analyze_modification_patterns(user_id)
        architecture_style = self._determine_architecture_preference(successful_projects)
        complexity_pref = self._analyze_complexity_preference(successful_projects)
        domain_expertise = self._extract_domain_expertise(successful_projects)
        
        return UserContext(
            user_id=user_id,
            successful_projects=[self._project_to_dict(p) for p in successful_projects],
            tech_stack_history=tech_stacks,
            frequent_features=features,
            common_modifications=modifications,
            architecture_style=architecture_style,
            complexity_preference=complexity_pref,
            domain_expertise=domain_expertise,
            generation_patterns=self._analyze_generation_patterns(user_id)
        )
    
    def _extract_tech_stacks(self, projects: List[Project]) -> List[str]:
        """Extract commonly used technology stacks"""
        tech_stacks = []
        for project in projects:
            if project.template_used:
                tech_stacks.append(project.template_used)
        return tech_stacks
    
    def _extract_common_features(self, projects: List[Project]) -> List[str]:
        """Extract frequently requested features"""
        all_features = []
        for project in projects:
            if hasattr(project, 'features_used') and project.features_used:
                all_features.extend(project.features_used)
        
        # Return top 5 most common features
        feature_counts = Counter(all_features)
        return [feature for feature, _ in feature_counts.most_common(5)]
    
    def _analyze_modification_patterns(self, user_id: str) -> List[str]:
        """Analyze common modifications user makes to generated code"""
        # This would analyze user's code modifications in a real implementation
        # For now, return common modification patterns
        return [
            "Add custom validation logic",
            "Modify database relationships",
            "Add additional endpoints",
            "Customize error handling",
            "Add business logic methods"
        ]
    
    def _determine_architecture_preference(self, projects: List[Project]) -> str:
        """Determine user's preferred architecture style"""
        # Analyze project structures to determine preference
        # For now, return a default
        if len(projects) > 5:
            return "microservices"
        elif len(projects) > 2:
            return "modular_monolith"
        else:
            return "simple_structure"
    
    def _analyze_complexity_preference(self, projects: List[Project]) -> str:
        """Analyze user's complexity preferences"""
        # Analyze project complexity levels
        if not projects:
            return "moderate"
        
        avg_entities = sum(
            len(project.entities) if hasattr(project, 'entities') and project.entities else 3 
            for project in projects
        ) / len(projects)
        
        if avg_entities > 8:
            return "high"
        elif avg_entities > 4:
            return "moderate"
        else:
            return "simple"
    
    def _extract_domain_expertise(self, projects: List[Project]) -> List[str]:
        """Extract domains where user has experience"""
        domains = []
        for project in projects:
            if hasattr(project, 'domain') and project.domain:
                domains.append(project.domain)
        
        domain_counts = Counter(domains)
        return [domain for domain, _ in domain_counts.most_common(3)]
    
    def _analyze_generation_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyze user's generation patterns and success rates"""
        generations = self.generation_repo.get_user_generations(user_id)
        
        if not generations:
            return {"total_generations": 0, "success_rate": 0.0}
        
        successful = sum(1 for gen in generations if gen.status == "completed")
        
        return {
            "total_generations": len(generations),
            "success_rate": successful / len(generations) if generations else 0.0,
            "avg_time_to_completion": self._calculate_avg_completion_time(generations),
            "common_failure_reasons": self._extract_failure_reasons(generations)
        }
    
    def _calculate_avg_completion_time(self, generations: List[Generation]) -> float:
        """Calculate average time to completion"""
        completed = [
            gen for gen in generations 
            if gen.status == "completed" and gen.completed_at and gen.created_at
        ]
        
        if not completed:
            return 0.0
        
        total_time = sum(
            (gen.completed_at - gen.created_at).total_seconds() 
            for gen in completed
        )
        
        return total_time / len(completed) / 60  # Return in minutes
    
    def _extract_failure_reasons(self, generations: List[Generation]) -> List[str]:
        """Extract common failure reasons"""
        failed = [gen for gen in generations if gen.status == "failed"]
        
        # In a real implementation, this would analyze error messages
        # For now, return common failure patterns
        return [
            "Complex business logic requirements",
            "Unclear requirements",
            "Unsupported technology stack",
            "Performance constraints"
        ]
    
    def _project_to_dict(self, project: Project) -> Dict[str, Any]:
        """Convert project to dictionary for context"""
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "features": getattr(project, 'features_used', []),
            "template": project.template_used,
            "status": project.status,
            "created_at": project.created_at.isoformat() if project.created_at else None
        }


class ProjectSimilarityMatcher:
    """Finds similar projects to provide relevant context"""
    
    def __init__(self, project_repository: ProjectRepository):
        self.project_repo = project_repository
    
    def find_similar_projects(
        self, 
        prompt: str, 
        user_context: UserContext,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find projects similar to the current prompt"""
        
        # Get all successful projects (not just user's)
        # For now, get public projects as a proxy for successful ones
        all_projects = self.project_repo.get_public_projects(limit=100)
        
        # Score projects by similarity
        scored_projects = []
        for project in all_projects:
            similarity_score = self._calculate_similarity_score(prompt, project, user_context)
            if similarity_score > 0.3:  # Minimum similarity threshold
                scored_projects.append((similarity_score, project))
        
        # Sort by similarity and return top matches
        scored_projects.sort(key=lambda x: x[0], reverse=True)
        
        return [
            self._project_to_dict(project) 
            for _, project in scored_projects[:limit]
        ]
    
    def _calculate_similarity_score(
        self, 
        prompt: str, 
        project: Project, 
        user_context: UserContext
    ) -> float:
        """Calculate similarity score between prompt and project"""
        
        score = 0.0
        
        # Text similarity (simplified keyword matching)
        prompt_keywords = self._extract_keywords(prompt.lower())
        project_keywords = self._extract_keywords(
            f"{project.description} {' '.join(getattr(project, 'features_used', []))}"
        )
        
        keyword_overlap = len(prompt_keywords.intersection(project_keywords))
        if prompt_keywords:
            score += (keyword_overlap / len(prompt_keywords)) * 0.4
        
        # Feature similarity
        if hasattr(project, 'features_used') and project.features_used:
            user_features = set(user_context.frequent_features)
            project_features = set(project.features_used)
            feature_overlap = len(user_features.intersection(project_features))
            if user_features:
                score += (feature_overlap / len(user_features)) * 0.3
        
        # Tech stack similarity
        if project.template_used in user_context.tech_stack_history:
            score += 0.2
        
        # Domain similarity
        if hasattr(project, 'domain') and project.domain in user_context.domain_expertise:
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _extract_keywords(self, text: str) -> set:
        """Extract relevant keywords from text"""
        # Simple keyword extraction (in practice, would use NLP libraries)
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during'
        }
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = {word for word in words if len(word) > 3 and word not in common_words}
        
        return keywords
    
    def _project_to_dict(self, project: Project) -> Dict[str, Any]:
        """Convert project to dictionary"""
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "features": getattr(project, 'features_used', []),
            "template": project.template_used,
            "domain": getattr(project, 'domain', None),
            "success_metrics": getattr(project, 'success_metrics', {})
        }


class ContextAwareOrchestrator:
    """Main orchestrator for context-aware code generation"""
    
    def __init__(
        self,
        pattern_analyzer: UserPatternAnalyzer,
        similarity_matcher: ProjectSimilarityMatcher,
        prompt_chain: PromptChain
    ):
        self.pattern_analyzer = pattern_analyzer
        self.similarity_matcher = similarity_matcher
        self.prompt_chain = prompt_chain
    
    def generate_with_context(self, prompt: str, user_id: str) -> Dict[str, Any]:
        """Generate code with full context awareness"""

        try:
            # 1. Analyze user patterns and context
            user_context = self.pattern_analyzer.analyze_user_patterns(user_id)

            # 2. Find similar successful projects
            similar_projects = self.similarity_matcher.find_similar_projects(
                prompt, user_context
            )

            # 3. Process through enhanced prompt chain
            enhanced_prompts = self.prompt_chain.process_prompt_chain(
                prompt, user_context, similar_projects
            )

            # 4. Generate context-enriched response
            generation_context = {
                "original_prompt": prompt,
                "user_context": user_context,
                "similar_projects": similar_projects,
                "enhanced_prompts": enhanced_prompts,
                "recommendations": self._generate_recommendations(user_context, similar_projects)
            }

            return generation_context

        except Exception as e:
            print(f"Error in generate_with_context: {e}")
            # Return minimal context on error
            return {
                "original_prompt": prompt,
                "user_context": {},
                "similar_projects": [],
                "enhanced_prompts": {},
                "recommendations": {}
            }
    
    def _generate_recommendations(
        self, 
        user_context: UserContext, 
        similar_projects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate recommendations based on context analysis"""
        
        recommendations = {
            "suggested_features": [],
            "tech_stack_recommendation": None,
            "architecture_advice": [],
            "potential_issues": [],
            "optimization_suggestions": []
        }
        
        # Feature recommendations based on user history
        if user_context.frequent_features:
            recommendations["suggested_features"] = user_context.frequent_features[:3]
        
        # Tech stack recommendation
        if user_context.tech_stack_history:
            most_used = Counter(user_context.tech_stack_history).most_common(1)[0][0]
            recommendations["tech_stack_recommendation"] = most_used
        
        # Architecture advice
        if user_context.complexity_preference == "high":
            recommendations["architecture_advice"].append(
                "Consider microservices architecture for better scalability"
            )
        elif user_context.complexity_preference == "simple":
            recommendations["architecture_advice"].append(
                "Monolithic architecture may be more appropriate for this complexity level"
            )
        
        # Potential issues based on similar projects
        if similar_projects:
            recommendations["potential_issues"] = [
                "Consider performance optimization for database queries",
                "Implement proper error handling and validation",
                "Plan for scalability from the beginning"
            ]
        
        # Optimization suggestions
        if "caching" in user_context.frequent_features:
            recommendations["optimization_suggestions"].append(
                "Implement Redis caching for frequently accessed data"
            )
        
        if "authentication" in user_context.frequent_features:
            recommendations["optimization_suggestions"].append(
                "Use JWT tokens with refresh mechanism for better security"
            )
        
        return recommendations


# Factory function for easy instantiation
def create_enhanced_prompt_system(
    project_repository: ProjectRepository,
    user_repository: UserRepository,
    generation_repository: GenerationRepository
) -> ContextAwareOrchestrator:
    """Create a fully configured enhanced prompt system"""
    
    pattern_analyzer = UserPatternAnalyzer(
        project_repository, user_repository, generation_repository
    )
    
    similarity_matcher = ProjectSimilarityMatcher(project_repository)
    
    prompt_chain = PromptChain()
    
    return ContextAwareOrchestrator(
        pattern_analyzer, similarity_matcher, prompt_chain
    )
