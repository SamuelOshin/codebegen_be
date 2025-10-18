"""
Prompt Analysis Service for Auto-Project Creation

Intelligently extracts project metadata from user prompts to enable
seamless project creation during generation flow.

Features:
- Entity extraction (nouns, technologies)
- Domain classification
- Tech stack detection
- Project name generation
- Complexity estimation
"""

import re
from loguru import logger
from typing import Dict, List, Optional, Tuple, Set
from collections import Counter
from dataclasses import dataclass

logger = logger


@dataclass
class PromptAnalysisResult:
    """Result of prompt analysis with extracted metadata"""
    suggested_name: str
    domain: str
    tech_stack: List[str]
    entities: List[str]
    features: List[str]
    complexity: str
    confidence: float
    description: str


class PromptAnalysisService:
    """
    Service for analyzing user prompts and extracting project metadata.
    
    Uses pattern matching, keyword extraction, and heuristics to understand
    user intent and suggest appropriate project configuration.
    """
    
    def __init__(self):
        self._initialize_detection_patterns()
    
    def _initialize_detection_patterns(self):
        """Initialize all detection patterns and mappings"""
        
        # Domain detection patterns
        self.domain_patterns = {
            "ecommerce": {
                "keywords": [
                    "shop", "store", "product", "cart", "order", "payment", 
                    "checkout", "inventory", "ecommerce", "marketplace", "buy", 
                    "sell", "price", "catalog", "shipping", "customer"
                ],
                "weight": 1.0
            },
            "social_media": {
                "keywords": [
                    "social", "post", "comment", "like", "follow", "follower",
                    "feed", "timeline", "share", "friend", "message", "chat",
                    "notification", "profile", "user interaction"
                ],
                "weight": 1.0
            },
            "content_management": {
                "keywords": [
                    "blog", "article", "content", "cms", "post", "page", 
                    "media", "publish", "editor", "draft", "category", "tag",
                    "author", "seo", "wordpress"
                ],
                "weight": 1.0
            },
            "task_management": {
                "keywords": [
                    "task", "project", "todo", "kanban", "board", "sprint",
                    "issue", "ticket", "workflow", "team", "assignee", "deadline",
                    "milestone", "progress", "jira", "trello"
                ],
                "weight": 1.0
            },
            "fintech": {
                "keywords": [
                    "bank", "payment", "finance", "transaction", "account",
                    "loan", "investment", "trading", "money", "currency",
                    "wallet", "credit", "debit", "ledger", "balance"
                ],
                "weight": 1.0
            },
            "healthcare": {
                "keywords": [
                    "patient", "doctor", "medical", "health", "appointment",
                    "clinic", "hospital", "treatment", "diagnosis", "prescription",
                    "healthcare", "ehr", "emr", "clinical"
                ],
                "weight": 1.0
            }
        }
        
        # Tech stack detection patterns
        self.tech_patterns = {
            "fastapi": ["fastapi", "fast api", "async python"],
            "django": ["django", "django rest"],
            "flask": ["flask"],
            "postgresql": ["postgres", "postgresql", "psql"],
            "mongodb": ["mongo", "mongodb", "nosql"],
            "sqlite": ["sqlite"],
            "redis": ["redis", "cache"],
            "celery": ["celery", "task queue", "background task"],
            "docker": ["docker", "container"],
            "kubernetes": ["k8s", "kubernetes"],
            "graphql": ["graphql"],
            "websocket": ["websocket", "real-time", "realtime"],
            "stripe": ["stripe", "payment processing"],
            "aws": ["aws", "amazon web services", "s3", "lambda"],
            "react": ["react", "reactjs"],
            "vue": ["vue", "vuejs"],
            "nextjs": ["next.js", "nextjs"]
        }
        
        # Entity extraction patterns
        self.common_entities = {
            "user", "product", "order", "payment", "customer", "item", 
            "post", "comment", "article", "category", "tag", "invoice", 
            "transaction", "account", "profile", "message", "notification",
            "file", "document", "task", "project", "team", "member",
            "patient", "doctor", "appointment", "review", "rating"
        }
        
        # Feature detection patterns
        self.feature_patterns = {
            "authentication": ["login", "register", "auth", "signin", "signup", "user management"],
            "authorization": ["permission", "role", "access control", "rbac"],
            "file_upload": ["upload", "file", "image", "media", "attachment", "document"],
            "search": ["search", "filter", "query", "elasticsearch", "full-text"],
            "notifications": ["notification", "email", "sms", "push", "alert"],
            "analytics": ["analytics", "dashboard", "metrics", "reporting", "stats"],
            "payments": ["payment", "stripe", "checkout", "billing", "subscription"],
            "real_time": ["real-time", "websocket", "live", "chat", "streaming"],
            "caching": ["cache", "redis", "performance"],
            "api": ["api", "rest", "graphql", "endpoint"],
            "admin": ["admin", "dashboard", "management panel"],
            "testing": ["test", "pytest", "unittest"]
        }
        
        # Action verbs that indicate project intent
        self.action_verbs = [
            "build", "create", "develop", "make", "design", "implement",
            "manage", "handle", "track", "monitor", "analyze"
        ]
        
        # Project type indicators
        self.project_types = {
            "api": ["api", "backend", "service", "microservice"],
            "platform": ["platform", "system", "application"],
            "dashboard": ["dashboard", "analytics", "monitoring"],
            "marketplace": ["marketplace", "multi-vendor"],
            "portal": ["portal", "customer portal", "admin portal"]
        }
    
    async def analyze_prompt(self, prompt: str, context: Optional[Dict] = None) -> PromptAnalysisResult:
        """
        Analyze prompt and extract project metadata.
        
        Args:
            prompt: User's generation prompt
            context: Optional context with user preferences or existing data
            
        Returns:
            PromptAnalysisResult with extracted metadata
        """
        prompt_lower = prompt.lower()
        
        # Extract components
        entities = self._extract_entities(prompt, prompt_lower)
        domain = self._detect_domain(prompt_lower, context)
        tech_stack = self._detect_tech_stack(prompt_lower, context)
        features = self._detect_features(prompt_lower)
        project_type = self._detect_project_type(prompt_lower)
        
        # Generate project name
        suggested_name = self._generate_project_name(
            prompt, entities, domain, project_type
        )
        
        # Generate description
        description = self._generate_description(
            prompt, domain, features, tech_stack
        )
        
        # Estimate complexity
        complexity = self._estimate_complexity(
            prompt, entities, features, tech_stack
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            domain, tech_stack, entities, features
        )
        
        return PromptAnalysisResult(
            suggested_name=suggested_name,
            domain=domain,
            tech_stack=tech_stack,
            entities=entities,
            features=features,
            complexity=complexity,
            confidence=confidence,
            description=description
        )
    
    def _extract_entities(self, prompt: str, prompt_lower: str) -> List[str]:
        """Extract entity names from prompt"""
        entities = set()
        
        # Check for common entities
        for entity in self.common_entities:
            if entity in prompt_lower or f"{entity}s" in prompt_lower:
                entities.add(entity.capitalize())
        
        # Extract from action patterns (e.g., "manage products", "create tasks")
        action_patterns = [
            r"(?:manage|create|handle|track|monitor)\s+(\w+)",
            r"(?:for|with)\s+(\w+)\s+(?:management|tracking|handling)",
            r"(\w+)\s+(?:api|service|system|platform)"
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, prompt_lower)
            for match in matches:
                if len(match) > 2 and match not in ["the", "and", "with", "for"]:
                    entities.add(match.capitalize())
        
        # Capitalize first letter of sentences as potential entities
        words = prompt.split()
        for i, word in enumerate(words):
            if word[0].isupper() and len(word) > 2 and word.lower() not in ["api", "rest"]:
                if word.lower() in self.common_entities:
                    entities.add(word)
        
        # Limit to most relevant 5 entities
        return list(entities)[:5]
    
    def _detect_domain(self, prompt_lower: str, context: Optional[Dict] = None) -> str:
        """Detect project domain using keyword matching"""
        
        # If domain is explicitly provided in context
        if context and "domain" in context:
            return context["domain"]
        
        domain_scores = {}
        
        for domain, config in self.domain_patterns.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in prompt_lower:
                    score += config["weight"]
            domain_scores[domain] = score
        
        # Return domain with highest score, or "general" as default
        if max(domain_scores.values(), default=0) > 0:
            return max(domain_scores, key=domain_scores.get)
        
        return "general"
    
    def _detect_tech_stack(self, prompt_lower: str, context: Optional[Dict] = None) -> List[str]:
        """Detect technologies mentioned in prompt"""
        
        detected_tech = set()
        
        # If tech_stack is explicitly provided in context
        if context and "tech_stack" in context:
            tech_str = context["tech_stack"]
            if isinstance(tech_str, str):
                detected_tech.update(tech_str.split("_"))
            elif isinstance(tech_str, list):
                detected_tech.update(tech_str)
        
        # Detect from prompt
        for tech, patterns in self.tech_patterns.items():
            if any(pattern in prompt_lower for pattern in patterns):
                detected_tech.add(tech)
        
        # Default to fastapi + postgres if nothing detected
        if not detected_tech:
            detected_tech = {"fastapi", "postgresql"}
        
        return list(detected_tech)
    
    def _detect_features(self, prompt_lower: str) -> List[str]:
        """Detect required features from prompt"""
        
        detected_features = set()
        
        for feature, patterns in self.feature_patterns.items():
            if any(pattern in prompt_lower for pattern in patterns):
                detected_features.add(feature)
        
        return list(detected_features)
    
    def _detect_project_type(self, prompt_lower: str) -> Optional[str]:
        """Detect project type (API, Platform, Dashboard, etc.)"""
        
        for proj_type, patterns in self.project_types.items():
            if any(pattern in prompt_lower for pattern in patterns):
                return proj_type
        
        return None
    
    def _generate_project_name(
        self, 
        prompt: str, 
        entities: List[str], 
        domain: str,
        project_type: Optional[str]
    ) -> str:
        """
        Generate a meaningful project name from prompt analysis.
        
        Priority:
        1. Extract explicit name from prompt (e.g., "Build a TaskMaster API")
        2. Combine main entity + project type (e.g., "Product API")
        3. Use domain + type (e.g., "E-commerce Platform")
        4. Use first 50 chars of prompt
        """
        
        # Pattern 1: Look for quoted names or capitalized phrases
        quoted_pattern = r'["\']([\w\s]+)["\']'
        quoted_matches = re.findall(quoted_pattern, prompt)
        if quoted_matches:
            return quoted_matches[0].strip()
        
        # Pattern 2: Look for "called X" or "named X"
        named_pattern = r'(?:called|named)\s+([\w\s]+?)(?:\s+(?:that|which|for)|$)'
        named_matches = re.findall(named_pattern, prompt, re.IGNORECASE)
        if named_matches:
            name = named_matches[0].strip()
            if len(name) < 50:
                return name.title()
        
        # Pattern 3: Primary entity + type
        if entities and project_type:
            primary_entity = entities[0]
            return f"{primary_entity} {project_type.title()}"
        
        # Pattern 4: Entity + "Management" or "System"
        if entities:
            primary_entity = entities[0]
            if "manage" in prompt.lower() or "track" in prompt.lower():
                return f"{primary_entity} Management"
            return f"{primary_entity} System"
        
        # Pattern 5: Domain-based name
        if domain != "general":
            domain_names = {
                "ecommerce": "E-commerce",
                "social_media": "Social Media",
                "content_management": "Content Management",
                "task_management": "Task Management",
                "fintech": "Financial",
                "healthcare": "Healthcare"
            }
            domain_label = domain_names.get(domain, domain.replace("_", " ").title())
            type_suffix = project_type.title() if project_type else "Platform"
            return f"{domain_label} {type_suffix}"
        
        # Pattern 6: Fallback - use first meaningful phrase from prompt
        words = prompt.split()
        meaningful_words = [
            w for w in words[:10] 
            if len(w) > 3 and w.lower() not in ["build", "create", "make", "with", "that", "this"]
        ]
        
        if meaningful_words:
            name = " ".join(meaningful_words[:4])
            if len(name) > 50:
                name = name[:47] + "..."
            return name.title()
        
        # Ultimate fallback
        return "Auto-Generated Project"
    
    def _generate_description(
        self,
        prompt: str,
        domain: str,
        features: List[str],
        tech_stack: List[str]
    ) -> str:
        """Generate project description from analysis"""
        
        # Use first sentence of prompt as base
        first_sentence = prompt.split('.')[0].strip()
        
        if len(first_sentence) > 200:
            first_sentence = first_sentence[:197] + "..."
        
        # Add domain context
        domain_desc = f"Domain: {domain.replace('_', ' ').title()}. "
        
        # Add tech stack
        tech_desc = f"Technologies: {', '.join(tech_stack)}. "
        
        # Add feature count
        feature_desc = f"Features: {len(features)} detected."
        
        full_desc = f"{first_sentence}. {domain_desc}{tech_desc}{feature_desc}"
        
        return full_desc
    
    def _estimate_complexity(
        self,
        prompt: str,
        entities: List[str],
        features: List[str],
        tech_stack: List[str]
    ) -> str:
        """
        Estimate project complexity.
        
        Returns: "simple", "moderate", or "complex"
        """
        complexity_score = 0
        
        # Factor 1: Prompt length
        word_count = len(prompt.split())
        if word_count > 100:
            complexity_score += 2
        elif word_count > 50:
            complexity_score += 1
        
        # Factor 2: Entity count
        complexity_score += len(entities) * 0.5
        
        # Factor 3: Feature count
        complexity_score += len(features)
        
        # Factor 4: Tech stack diversity
        complexity_score += len(tech_stack) * 0.3
        
        # Factor 5: Complex keywords
        complex_keywords = [
            "microservice", "scalable", "distributed", "real-time",
            "multi-tenant", "high-traffic", "enterprise", "advanced"
        ]
        prompt_lower = prompt.lower()
        complexity_score += sum(
            2 for keyword in complex_keywords if keyword in prompt_lower
        )
        
        # Classify based on score
        if complexity_score < 3:
            return "simple"
        elif complexity_score < 8:
            return "moderate"
        else:
            return "complex"
    
    def _calculate_confidence(
        self,
        domain: str,
        tech_stack: List[str],
        entities: List[str],
        features: List[str]
    ) -> float:
        """
        Calculate confidence score for the analysis.
        
        Returns: Float between 0.0 and 1.0
        """
        confidence = 0.5  # Base confidence
        
        # Increase confidence if domain is detected (not general)
        if domain != "general":
            confidence += 0.2
        
        # Increase confidence if entities are found
        if entities:
            confidence += min(len(entities) * 0.05, 0.15)
        
        # Increase confidence if features are detected
        if features:
            confidence += min(len(features) * 0.03, 0.1)
        
        # Increase confidence if tech stack is specific
        if len(tech_stack) > 1:
            confidence += 0.05
        
        return min(confidence, 1.0)


# Singleton instance
prompt_analysis_service = PromptAnalysisService()
