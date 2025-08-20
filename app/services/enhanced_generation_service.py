"""
Enhanced Generation Service

Integrates the Advanced Template System with the Enhanced Prompt Engineering System
for Phase 2 of the Two-Week Validation Test.

This service coordinates between:
1. Template-based generation (Phase 1)
2. Enhanced prompt engineering (Phase 2)
3. Context-aware AI orchestration
"""

from typing import Dict, List, Any, Optional, Tuple
import json
import time
from datetime import datetime

from app.services.advanced_template_system import AdvancedTemplateSystem
from app.services.enhanced_prompt_system import ContextAwareOrchestrator, create_enhanced_prompt_system
from app.services.ai_orchestrator import AIOrchestrator
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.repositories.generation_repository import GenerationRepository
from app.core.config import settings


class EnhancedGenerationService:
    """
    Main service for coordinating enhanced code generation
    
    Combines template-based generation with enhanced prompt engineering
    for optimal results based on user context and patterns.
    """
    
    def __init__(
        self,
        project_repository: ProjectRepository,
        user_repository: UserRepository,
        generation_repository: GenerationRepository
    ):
        self.project_repo = project_repository
        self.user_repo = user_repository
        self.generation_repo = generation_repository
        
        # Initialize systems
        self.template_system = AdvancedTemplateSystem()
        self.enhanced_prompt_system: Optional[ContextAwareOrchestrator] = None
        self.ai_orchestrator = AIOrchestrator()
        
        # Configuration
        self.enable_enhanced_prompts = True
        self.enable_template_fallback = True
        self.enable_hybrid_mode = True
    
    async def initialize(self):
        """Initialize all subsystems"""
        print("Initializing Enhanced Generation Service...")
        
        try:
            # Initialize enhanced prompt system
            self.enhanced_prompt_system = create_enhanced_prompt_system(
                self.project_repo, self.user_repo, self.generation_repo
            )
            print("✅ Enhanced Prompt System initialized")
            
            # Initialize AI orchestrator
            await self.ai_orchestrator.initialize()
            print("✅ AI Orchestrator initialized")
            
            print("🚀 Enhanced Generation Service ready!")
            
        except Exception as e:
            print(f"⚠️ Warning: Enhanced systems initialization failed: {e}")
            print("Falling back to basic template generation")
            self.enable_enhanced_prompts = False
            
        # Initialize memory-efficient service as additional fallback
        try:
            from app.services.memory_efficient_service import memory_efficient_service
            self.memory_efficient_service = memory_efficient_service
            await self.memory_efficient_service.initialize()
            print("✅ Memory-efficient service integrated")
        except Exception as e:
            print(f"⚠️ Warning: Memory-efficient service initialization failed: {e}")
            self.memory_efficient_service = None
    
    async def generate_project(
        self,
        prompt: str,
        user_id: str,
        domain: Optional[str] = None,
        tech_stack: Optional[str] = None,
        use_enhanced_prompts: bool = True,
        use_templates: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a project using Qwen Inference as default for memory efficiency
        with template and AI generation fallback strategies.
        
        Args:
            prompt: User's project description
            user_id: User identifier for context analysis
            domain: Optional domain specification
            tech_stack: Optional technology stack preference
            use_enhanced_prompts: Whether to use enhanced prompt engineering
            use_templates: Whether to consider template-based generation
            
        Returns:
            Complete generation result with files, metadata, and recommendations
        """
        
        generation_start = time.time()
        
        # Check memory availability for strategy selection
        memory_available = True
        if self.memory_efficient_service:
            memory_available = await self.memory_efficient_service.can_use_ai_models()
        
        try:
            # Check if forced to use Qwen Inference mode
            if settings.FORCE_INFERENCE_MODE:
                print("⚡ Using forced Qwen Inference mode")
                return await self._generate_with_qwen_inference_direct(
                    prompt, user_id, domain, tech_stack
                )
            
            # Strategy 1: Qwen Inference (preferred for memory efficiency)
            if self.enable_enhanced_prompts and use_enhanced_prompts:
                print("🚀 Attempting Qwen Inference generation")
                try:
                    return await self._generate_with_qwen_inference_direct(
                        prompt, user_id, domain, tech_stack
                    )
                except Exception as e:
                    print(f"⚠️ Qwen Inference failed: {e}")
                    print("Falling back to AI orchestrator")
            
            # Strategy 2: Full AI generation (if memory allows and enhanced prompts enabled)
            if memory_available and self.enable_enhanced_prompts and use_enhanced_prompts:
                print("🚀 Attempting full AI generation with enhanced prompts")
                try:
                    return await self._generate_with_ai_orchestrator(
                        prompt, user_id, domain, tech_stack
                    )
                except Exception as e:
                    print(f"⚠️ Full AI generation failed: {e}")
                    print("Falling back to memory-efficient strategy")
            
            # Strategy 3: Memory-efficient generation
            if self.memory_efficient_service and use_templates:
                print("📝 Using memory-efficient template generation")
                try:
                    result = await self.memory_efficient_service.generate_project(
                        prompt=prompt,
                        tech_stack=tech_stack or "fastapi",
                        domain=domain or "general",
                        features=self._extract_features_from_prompt(prompt),
                        user_context={"user_id": user_id}
                    )
                    
                    # Add enhanced metadata
                    result.update({
                        "generation_time": time.time() - generation_start,
                        "strategy_path": "memory_efficient",
                        "user_id": user_id
                    })
                    
                    return result
                    
                except Exception as e:
                    print(f"⚠️ Memory-efficient generation failed: {e}")
            
            # Strategy 4: Basic template fallback
            if self.enable_template_fallback:
                print("📄 Using basic template generation")
                return await self._generate_with_basic_templates(
                    prompt, domain, tech_stack
                )
            
            # Strategy 5: Minimal fallback
            raise Exception("All generation strategies failed")
            
        except Exception as e:
            print(f"❌ Enhanced generation failed: {e}")
            return await self._minimal_fallback(prompt, user_id)
    
    async def analyze_context(
        self, 
        prompt: str, 
        project_context: Dict[str, Any], 
        tech_stack: str
    ) -> Dict[str, Any]:
        """
        Analyze the context for enhanced generation
        
        Args:
            prompt: User's generation prompt
            project_context: Additional context provided by user
            tech_stack: Selected technology stack
            
        Returns:
            Dictionary containing context analysis results
        """
        try:
            # Initialize enhanced prompt system if needed
            if not self.enhanced_prompt_system:
                await self.initialize()
            
            # Base context analysis
            context_analysis = {
                "tech_stack": tech_stack,
                "project_context": project_context,
                "prompt_complexity": self._analyze_prompt_complexity(prompt),
                "extracted_features": self._extract_features_from_prompt(prompt),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Enhanced context analysis if system is available
            if self.enhanced_prompt_system:
                try:
                    # Use the enhanced prompt system for deeper analysis
                    enhanced_context = self.enhanced_prompt_system.generate_with_context(
                        prompt, 
                        "system_user"  # Use system user for context analysis
                    )
                    
                    if isinstance(enhanced_context, dict):
                        context_analysis.update({
                            "enhanced_analysis": enhanced_context,
                            "user_context": enhanced_context.get("user_context", {}),
                            "similar_projects": enhanced_context.get("similar_projects", []),
                            "recommended_patterns": enhanced_context.get("patterns", [])
                        })
                except Exception as e:
                    print(f"Enhanced context analysis failed: {e}")
                    context_analysis["enhanced_analysis_error"] = str(e)
            
            # Analyze template suitability
            template_analysis = await self._analyze_template_suitability(
                prompt, tech_stack, "system_user"
            )
            context_analysis["template_analysis"] = template_analysis
            
            return context_analysis
            
        except Exception as e:
            print(f"Context analysis failed: {e}")
            return {
                "error": str(e),
                "tech_stack": tech_stack,
                "project_context": project_context,
                "fallback_analysis": True,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _extract_features_from_prompt(self, prompt: str) -> List[str]:
        """Extract feature requirements from prompt"""
        features = []
        feature_keywords = {
            "auth": ["authentication", "login", "register", "user", "account"],
            "upload": ["upload", "file", "image", "document"],
            "realtime": ["realtime", "websocket", "live", "streaming"],
            "cache": ["cache", "redis", "performance"],
            "search": ["search", "find", "query", "filter"],
            "payments": ["payment", "billing", "stripe", "checkout"],
            "notifications": ["notification", "email", "alert", "message"],
            "admin": ["admin", "dashboard", "management", "control"]
        }
        
        prompt_lower = prompt.lower()
        for feature, keywords in feature_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                features.append(feature)
        
        return features
    
    async def _generate_with_qwen_inference_direct(
        self, prompt: str, user_id: str, domain: Optional[str], tech_stack: Optional[str]
    ) -> Dict[str, Any]:
        """Generate using Qwen Inference API directly - bypasses orchestrator overhead"""
        from ai_models.qwen_generator import QwenGenerator
        
        print("🤖 Using Qwen Inference API for direct generation")
        
        qwen = QwenGenerator(model_path=settings.QWEN_LARGE_MODEL_PATH)
        await qwen.load()
        
        # Create comprehensive schema for generation
        schema = {
            "domain": domain or "general",
            "tech_stack": tech_stack or "fastapi_postgresql",
            "features": self._extract_features_from_prompt(prompt),
            "entities": [],
            "endpoints": []
        }
        
        # Enhanced context for better generation
        context = {
            "domain": domain or "general",
            "tech_stack": tech_stack or "fastapi_postgresql",
            "user_id": user_id,
            "generation_method": "qwen_inference_direct",
            "constraints": [
                "Follow PEP8 and FastAPI best practices",
                "Include proper error handling",
                "Generate production-ready code",
                "Include tests and documentation"
            ]
        }
        
        try:
            # Generate project using Qwen
            files = await qwen.generate_project(
                prompt=prompt,
                schema=schema,
                context=context
            )
            
            return {
                "files": files,
                "schema": schema,
                "generation_method": "qwen_inference_direct",
                "model_used": settings.QWEN_LARGE_MODEL_PATH,
                "quality_score": 0.85,  # High quality expected from latest Qwen model
                "user_id": user_id,
                "context_analysis": {
                    "features_detected": schema["features"],
                    "generation_strategy": "direct_inference"
                }
            }
            
        except Exception as e:
            print(f"Direct Qwen generation failed: {e}")
            raise

    async def _generate_with_ai_orchestrator(
        self, prompt: str, user_id: str, domain: Optional[str], tech_stack: Optional[str]
    ) -> Dict[str, Any]:
        """Generate using full AI orchestrator"""
        from app.services.ai_orchestrator import GenerationRequest
        
        request = GenerationRequest(
            prompt=prompt,
            context={
                "domain": domain or "general",
                "tech_stack": tech_stack or "fastapi",
                "user_id": user_id
            },
            user_id=user_id,
            use_enhanced_prompts=True
        )
        
        # Use memory-aware generation if available
        if hasattr(self.ai_orchestrator, 'generate_project_memory_aware'):
            result = await self.ai_orchestrator.generate_project_memory_aware(request)
        else:
            result = await self.ai_orchestrator.generate_project(request)
        
        # Convert to expected format
        return {
            "files": result.files,
            "schema": result.schema,
            "review_feedback": result.review_feedback,
            "documentation": result.documentation,
            "quality_score": result.quality_score,
            "strategy_used": "full_ai_orchestrator"
        }
    
    async def _generate_with_basic_templates(
        self, prompt: str, domain: Optional[str], tech_stack: Optional[str]
    ) -> Dict[str, Any]:
        """Generate using basic template system"""
        requirements = {
            "tech_stack": tech_stack or "fastapi",
            "domain": domain or "general",
            "features": self._extract_features_from_prompt(prompt)
        }
        
        return self.template_system.generate_project(prompt, requirements)
    
    async def _minimal_fallback(self, prompt: str, user_id: str) -> Dict[str, Any]:
        """Absolute minimal fallback generation"""
        from app.services.memory_efficient_service import quick_generate
        
        result = await quick_generate("fastapi")
        result.update({
            "strategy_used": "minimal_fallback",
            "user_id": user_id,
            "generation_time": 0.1
        })
        
        return result
        
        start_time = time.time()
        generation_metadata = {
            "start_time": start_time,
            "prompt": prompt,
            "user_id": user_id,
            "domain": domain,
            "tech_stack": tech_stack,
            "use_enhanced_prompts": use_enhanced_prompts,
            "use_templates": use_templates
        }
        
        try:
            # Phase 1: Analyze and decide generation strategy
            strategy = await self._determine_generation_strategy(
                prompt, user_id, domain, tech_stack, use_enhanced_prompts, use_templates
            )
            
            generation_metadata["strategy"] = strategy
            
            # Phase 2: Execute generation based on strategy
            if strategy["approach"] == "template_only":
                result = await self._generate_with_templates_only(prompt, user_id, domain, tech_stack)
            elif strategy["approach"] == "ai_only":
                result = await self._generate_with_ai_only(prompt, user_id, domain, tech_stack, use_enhanced_prompts)
            elif strategy["approach"] == "hybrid":
                result = await self._generate_hybrid(prompt, user_id, domain, tech_stack, use_enhanced_prompts)
            else:
                raise ValueError(f"Unknown generation strategy: {strategy['approach']}")
            
            # Phase 3: Post-process and enhance results
            enhanced_result = await self._post_process_results(result, strategy, generation_metadata)
            
            generation_time = time.time() - start_time
            enhanced_result["generation_metadata"]["total_time"] = generation_time
            
            return enhanced_result
            
        except Exception as e:
            print(f"Error in enhanced generation: {e}")
            # Fallback to basic template generation
            return await self._fallback_generation(prompt, user_id, domain, tech_stack)
    
    async def _determine_generation_strategy(
        self,
        prompt: str,
        user_id: str,
        domain: Optional[str],
        tech_stack: Optional[str],
        use_enhanced_prompts: bool,
        use_templates: bool
    ) -> Dict[str, Any]:
        """Determine the optimal generation strategy"""
        
        strategy = {
            "approach": "hybrid",  # Default
            "confidence": 0.5,
            "reasoning": [],
            "template_suitable": False,
            "ai_suitable": True,
            "hybrid_suitable": True
        }
        
        # Analyze template suitability
        if use_templates:
            template_analysis = await self._analyze_template_suitability(prompt, domain, tech_stack)
            strategy["template_suitable"] = template_analysis["suitable"]
            strategy["template_analysis"] = template_analysis
            
            if template_analysis["suitable"] and template_analysis["confidence"] > 0.8:
                strategy["reasoning"].append(f"High template confidence: {template_analysis['confidence']:.2f}")
        
        # Analyze complexity
        complexity_analysis = self._analyze_prompt_complexity(prompt)
        strategy["complexity_analysis"] = complexity_analysis
        
        # Analyze user context if enhanced prompts are enabled
        if use_enhanced_prompts and self.enhanced_prompt_system:
            try:
                context_analysis = self.enhanced_prompt_system.generate_with_context(prompt, user_id)
                strategy["context_analysis"] = context_analysis
                
                # Ensure context_analysis is a dictionary
                if isinstance(context_analysis, dict):
                    user_context = context_analysis.get("user_context", {})
                    if isinstance(user_context, dict) and user_context.get("successful_projects"):
                        strategy["reasoning"].append("User has successful project history")
                    
                    if context_analysis.get("similar_projects"):
                        strategy["reasoning"].append("Found similar successful projects")
                else:
                    print(f"Warning: Context analysis returned unexpected type: {type(context_analysis)}")
                    strategy["reasoning"].append("Context analysis format error")
            except Exception as e:
                print(f"Warning: Context analysis failed: {e}")
                strategy["reasoning"].append("Context analysis unavailable")
        
        # Decision logic
        if (strategy["template_suitable"] and 
            complexity_analysis["complexity_score"] < 0.6 and
            not use_enhanced_prompts):
            strategy["approach"] = "template_only"
            strategy["confidence"] = 0.8
            strategy["reasoning"].append("Simple project suitable for templates")
            
        elif (complexity_analysis["complexity_score"] > 0.8 or
              not strategy["template_suitable"]):
            strategy["approach"] = "ai_only"
            strategy["confidence"] = 0.7
            strategy["reasoning"].append("Complex requirements need AI generation")
            
        else:
            strategy["approach"] = "hybrid"
            strategy["confidence"] = 0.9
            strategy["reasoning"].append("Hybrid approach for optimal results")
        
        return strategy
    
    async def _analyze_template_suitability(
        self, 
        prompt: str, 
        domain: Optional[str], 
        tech_stack: Optional[str]
    ) -> Dict[str, Any]:
        """Analyze if the prompt is suitable for template-based generation"""
        
        # Use the template system's analysis capabilities
        try:
            analysis = self.template_system.analyze_prompt_for_templates(prompt, domain, tech_stack)
            return {
                "suitable": analysis.get("suitable", False),
                "confidence": analysis.get("confidence", 0.5),
                "recommended_template": analysis.get("recommended_template"),
                "missing_features": analysis.get("missing_features", []),
                "complexity_factors": analysis.get("complexity_factors", [])
            }
        except Exception as e:
            print(f"Template analysis failed: {e}")
            return {
                "suitable": False,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _analyze_prompt_complexity(self, prompt: str) -> Dict[str, Any]:
        """Analyze the complexity of the prompt"""
        
        complexity_indicators = {
            "length": len(prompt.split()),
            "technical_terms": 0,
            "business_logic_words": 0,
            "integration_words": 0,
            "custom_requirements": 0
        }
        
        prompt_lower = prompt.lower()
        
        # Technical complexity indicators
        technical_terms = [
            "microservice", "api", "database", "authentication", "authorization",
            "payment", "integration", "webhook", "real-time", "caching", "search",
            "analytics", "machine learning", "ai", "blockchain", "encryption"
        ]
        
        business_logic_terms = [
            "workflow", "approval", "validation", "business rule", "custom logic",
            "complex calculation", "reporting", "dashboard", "analytics"
        ]
        
        integration_terms = [
            "third-party", "external api", "integration", "webhook", "sync",
            "import", "export", "migration", "connector"
        ]
        
        for term in technical_terms:
            if term in prompt_lower:
                complexity_indicators["technical_terms"] += 1
        
        for term in business_logic_terms:
            if term in prompt_lower:
                complexity_indicators["business_logic_words"] += 1
        
        for term in integration_terms:
            if term in prompt_lower:
                complexity_indicators["integration_words"] += 1
        
        # Calculate overall complexity score
        length_score = min(complexity_indicators["length"] / 100, 1.0)  # Normalize to 0-1
        technical_score = min(complexity_indicators["technical_terms"] / 5, 1.0)
        business_score = min(complexity_indicators["business_logic_words"] / 3, 1.0)
        integration_score = min(complexity_indicators["integration_words"] / 3, 1.0)
        
        complexity_score = (
            length_score * 0.2 +
            technical_score * 0.3 +
            business_score * 0.3 +
            integration_score * 0.2
        )
        
        return {
            "complexity_score": complexity_score,
            "indicators": complexity_indicators,
            "assessment": self._get_complexity_assessment(complexity_score)
        }
    
    def _get_complexity_assessment(self, score: float) -> str:
        """Get human-readable complexity assessment"""
        if score < 0.3:
            return "simple"
        elif score < 0.6:
            return "moderate"
        elif score < 0.8:
            return "complex"
        else:
            return "very_complex"
    
    async def _generate_with_templates_only(
        self,
        prompt: str,
        user_id: str,
        domain: Optional[str],
        tech_stack: Optional[str]
    ) -> Dict[str, Any]:
        """Generate project using only template system"""
        
        print("🎯 Using template-only generation")
        
        # Use advanced template system
        template_result = self.template_system.generate_project_from_prompt(
            prompt=prompt,
            domain=domain,
            tech_stack=tech_stack,
            user_id=user_id
        )
        
        return {
            "files": template_result.get("files", {}),
            "schema": template_result.get("schema", {}),
            "template_info": template_result.get("template_info", {}),
            "generation_method": "template_only",
            "quality_score": template_result.get("quality_score", 0.8)
        }
    
    async def _generate_with_ai_only(
        self,
        prompt: str,
        user_id: str,
        domain: Optional[str],
        tech_stack: Optional[str],
        use_enhanced_prompts: bool
    ) -> Dict[str, Any]:
        """Generate project using only AI generation"""
        
        print("🤖 Using AI-only generation")
        
        # Prepare generation data
        generation_data = {
            "prompt": prompt,
            "user_id": user_id,
            "domain": domain or "general",
            "tech_stack": tech_stack or "fastapi_postgres",
            "use_enhanced_prompts": use_enhanced_prompts
        }
        
        # Create a temporary generation record
        generation_id = f"temp_{int(time.time())}"
        
        # Process with AI orchestrator
        await self.ai_orchestrator.process_generation(generation_id, generation_data)
        
        # Get results (in real implementation, would retrieve from database)
        return {
            "files": {},  # Would be populated from actual generation
            "schema": {},
            "generation_method": "ai_only",
            "enhanced_prompts_used": use_enhanced_prompts,
            "quality_score": 0.85
        }
    
    async def _generate_hybrid(
        self,
        prompt: str,
        user_id: str,
        domain: Optional[str],
        tech_stack: Optional[str],
        use_enhanced_prompts: bool
    ) -> Dict[str, Any]:
        """Generate project using hybrid template + AI approach"""
        
        print("🔄 Using hybrid generation")
        
        # Start with template generation
        template_result = await self._generate_with_templates_only(
            prompt, user_id, domain, tech_stack
        )
        
        # Enhance with AI if enhanced prompts are enabled
        if use_enhanced_prompts and self.enhanced_prompt_system:
            try:
                # Get context analysis
                context_analysis = self.enhanced_prompt_system.generate_with_context(prompt, user_id)
                
                # Ensure context_analysis is a dictionary
                if isinstance(context_analysis, dict):
                    # Apply AI enhancements to template result
                    enhanced_files = await self._enhance_template_with_ai(
                        template_result["files"], 
                        context_analysis,
                        prompt
                    )
                    
                    template_result["files"] = enhanced_files
                    template_result["context_analysis"] = context_analysis
                    template_result["generation_method"] = "hybrid_enhanced"
                    template_result["quality_score"] = min(1.0, template_result["quality_score"] + 0.1)
                else:
                    print(f"Warning: Context analysis returned unexpected type: {type(context_analysis)}")
                    template_result["generation_method"] = "hybrid_template_fallback"
                
            except Exception as e:
                print(f"AI enhancement failed, using template result: {e}")
                template_result["generation_method"] = "hybrid_template_fallback"
        
        return template_result
    
    async def _enhance_template_with_ai(
        self,
        template_files: Dict[str, str],
        context_analysis: Dict[str, Any],
        original_prompt: str
    ) -> Dict[str, str]:
        """Enhance template-generated files with AI improvements"""
        
        enhanced_files = template_files.copy()
        
        # Ensure context_analysis is a dictionary
        if not isinstance(context_analysis, dict):
            print(f"Warning: context_analysis is not a dict: {type(context_analysis)}")
            return enhanced_files
        
        # Get user context and recommendations
        user_context = context_analysis.get("user_context", {})
        recommendations = context_analysis.get("recommendations", {})
        
        # Ensure user_context and recommendations are dictionaries
        if not isinstance(user_context, dict):
            user_context = {}
        if not isinstance(recommendations, dict):
            recommendations = {}
        
        # Add context-aware improvements
        if recommendations.get("suggested_features"):
            # Add suggested feature implementations
            for feature in recommendations["suggested_features"][:2]:  # Limit to top 2
                if feature not in template_files:
                    feature_implementation = self._generate_feature_implementation(feature, user_context)
                    if feature_implementation:
                        enhanced_files[f"app/features/{feature}.py"] = feature_implementation
        
        # Enhance existing files with user patterns
        if isinstance(user_context, dict) and user_context.get("common_modifications"):
            for file_path, content in enhanced_files.items():
                if file_path.endswith(".py"):
                    enhanced_content = self._apply_user_patterns(content, user_context)
                    enhanced_files[file_path] = enhanced_content
        
        return enhanced_files
    
    def _generate_feature_implementation(self, feature: str, user_context: Dict[str, Any]) -> Optional[str]:
        """Generate a basic implementation for a suggested feature"""
        
        feature_templates = {
            "authentication": '''"""
Authentication feature implementation
Based on user preferences and patterns
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import jwt

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    """Extract user from JWT token"""
    try:
        payload = jwt.decode(token.credentials, "secret", algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
''',
            
            "caching": '''"""
Caching feature implementation
Based on user preferences and patterns
"""

import redis
from functools import wraps
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiration: int = 300):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, expiration, json.dumps(result))
            return result
        return wrapper
    return decorator
''',
            
            "payments": '''"""
Payment processing feature implementation
Based on user preferences and patterns
"""

import stripe
from fastapi import HTTPException

stripe.api_key = "your-stripe-secret-key"

async def create_payment_intent(amount: int, currency: str = "usd"):
    """Create a Stripe payment intent"""
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            automatic_payment_methods={'enabled': True}
        )
        return {"client_secret": intent.client_secret}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
'''
        }
        
        return feature_templates.get(feature)
    
    def _apply_user_patterns(self, content: str, user_context: Dict[str, Any]) -> str:
        """Apply user's common modification patterns to content"""
        
        enhanced_content = content
        
        # Ensure user_context is a dictionary
        if not isinstance(user_context, dict):
            return enhanced_content
        
        # Apply common modifications based on user patterns
        common_mods = user_context.get("common_modifications", [])
        
        if "Add logging" in common_mods and "import logging" not in content:
            # Add logging import and setup
            logging_setup = '''
import logging

logger = logging.getLogger(__name__)
'''
            enhanced_content = logging_setup + enhanced_content
        
        if "Custom validation" in common_mods and "def validate_" not in content:
            # Add validation function template
            validation_template = '''

def validate_input(data: dict) -> bool:
    """Custom validation logic"""
    # Add your validation rules here
    return True
'''
            enhanced_content += validation_template
        
        return enhanced_content
    
    async def _post_process_results(
        self,
        result: Dict[str, Any],
        strategy: Dict[str, Any],
        generation_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Post-process generation results with additional metadata and improvements"""
        
        enhanced_result = result.copy()
        
        # Add comprehensive metadata
        enhanced_result["generation_metadata"] = generation_metadata
        enhanced_result["strategy_used"] = strategy
        enhanced_result["enhancement_version"] = "2.0"
        enhanced_result["timestamp"] = datetime.now().isoformat()
        
        # Add quality metrics
        quality_metrics = self._calculate_quality_metrics(result, strategy)
        enhanced_result["quality_metrics"] = quality_metrics
        
        # Add recommendations for improvement
        improvement_suggestions = self._generate_improvement_suggestions(result, strategy)
        enhanced_result["improvement_suggestions"] = improvement_suggestions
        
        return enhanced_result
    
    def _calculate_quality_metrics(self, result: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate quality metrics for the generated project"""
        
        metrics = {
            "file_count": len(result.get("files", {})),
            "total_lines": sum(len(content.split('\n')) for content in result.get("files", {}).values()),
            "base_quality_score": result.get("quality_score", 0.8),
            "strategy_bonus": 0.0,
            "enhanced_features": 0
        }
        
        # Strategy-based bonuses
        if strategy["approach"] == "hybrid":
            metrics["strategy_bonus"] = 0.05
        elif strategy["approach"] == "ai_only" and strategy.get("enhanced_prompts_used"):
            metrics["strategy_bonus"] = 0.03
        
        # Count enhanced features
        files = result.get("files", {})
        for file_path in files.keys():
            if "feature" in file_path.lower() or "enhanced" in file_path.lower():
                metrics["enhanced_features"] += 1
        
        # Calculate final score
        metrics["final_quality_score"] = min(1.0, 
            metrics["base_quality_score"] + metrics["strategy_bonus"]
        )
        
        return metrics
    
    def _generate_improvement_suggestions(self, result: Dict[str, Any], strategy: Dict[str, Any]) -> List[str]:
        """Generate suggestions for improving the generated project"""
        
        suggestions = []
        
        files = result.get("files", {})
        file_count = len(files)
        
        # File structure suggestions
        if file_count < 5:
            suggestions.append("Consider adding more modular structure with separate service and schema files")
        
        # Testing suggestions
        test_files = [f for f in files.keys() if "test" in f.lower()]
        if not test_files:
            suggestions.append("Add comprehensive unit tests for better code reliability")
        
        # Documentation suggestions
        readme_files = [f for f in files.keys() if "readme" in f.lower()]
        if not readme_files:
            suggestions.append("Include detailed README with setup and usage instructions")
        
        # Security suggestions
        if strategy.get("context_analysis", {}).get("recommendations", {}).get("potential_issues"):
            suggestions.append("Review and address potential security issues identified in similar projects")
        
        # Performance suggestions
        if file_count > 10:
            suggestions.append("Consider implementing caching and database optimization for better performance")
        
        return suggestions
    
    async def _fallback_generation(
        self,
        prompt: str,
        user_id: str,
        domain: Optional[str],
        tech_stack: Optional[str]
    ) -> Dict[str, Any]:
        """Fallback to basic template generation if enhanced systems fail"""
        
        print("⚠️ Using fallback generation")
        
        try:
            # Use basic template system
            basic_result = self.template_system.generate_project_from_prompt(
                prompt=prompt,
                domain=domain,
                tech_stack=tech_stack,
                user_id=user_id
            )
            
            basic_result["generation_method"] = "fallback_template"
            basic_result["quality_score"] = 0.7  # Lower score for fallback
            
            return basic_result
            
        except Exception as e:
            print(f"Fallback generation also failed: {e}")
            
            # Ultimate fallback - return minimal structure
            return {
                "files": {
                    "main.py": "# Generated FastAPI application\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\ndef read_root():\n    return {'message': 'Hello World'}"
                },
                "generation_method": "minimal_fallback",
                "quality_score": 0.5,
                "error": str(e)
            }


def create_enhanced_generation_service(
    project_repository: ProjectRepository,
    user_repository: UserRepository,
    generation_repository: GenerationRepository
) -> EnhancedGenerationService:
    """Factory function to create Enhanced Generation Service"""
    
    return EnhancedGenerationService(
        project_repository=project_repository,
        user_repository=user_repository,
        generation_repository=generation_repository
    )
