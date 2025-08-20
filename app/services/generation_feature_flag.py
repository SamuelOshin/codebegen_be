"""
Feature flag service for determining generation modes and routing logic.
Centralizes feature flagging decisions for enhanced vs classic generation.
"""

import hashlib
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.schemas.unified_generation import GenerationMode
from app.services.enhanced_ab_testing import enhanced_ab_test_manager
from app.core.config import settings


class FeatureFlagGroup(str, Enum):
    """Feature flag groups"""
    CONTROL = "control"
    ENHANCED_PROMPTS = "enhanced_prompts"
    HYBRID_GENERATION = "hybrid_generation"
    FULL_ENHANCEMENT = "full_enhancement"


@dataclass
class GenerationConfig:
    """Configuration for generation processing"""
    mode: GenerationMode
    use_enhanced_prompts: bool
    use_context_analysis: bool
    use_user_patterns: bool
    use_hybrid_generation: bool
    use_ab_testing: bool
    use_metrics_tracking: bool
    ab_group: Optional[str] = None
    features_enabled: Optional[Dict[str, bool]] = None
    expected_improvement: float = 0.0


class GenerationFeatureFlag:
    """
    Service for determining which generation mode and features to use.
    Integrates with A/B testing and provides backward compatibility.
    """
    
    def __init__(self):
        self.enhanced_ab_manager = enhanced_ab_test_manager
        
        # Default feature configurations
        self.feature_configs = {
            FeatureFlagGroup.CONTROL: {
                "enhanced_prompts": False,
                "context_analysis": False,
                "user_patterns": False,
                "hybrid_generation": False
            },
            FeatureFlagGroup.ENHANCED_PROMPTS: {
                "enhanced_prompts": True,
                "context_analysis": True,
                "user_patterns": False,
                "hybrid_generation": False
            },
            FeatureFlagGroup.HYBRID_GENERATION: {
                "enhanced_prompts": True,
                "context_analysis": True,
                "user_patterns": True,
                "hybrid_generation": True
            },
            FeatureFlagGroup.FULL_ENHANCEMENT: {
                "enhanced_prompts": True,
                "context_analysis": True,
                "user_patterns": True,
                "hybrid_generation": True
            }
        }
    
    def get_generation_config(
        self, 
        user_id: str, 
        requested_mode: GenerationMode,
        is_iteration: bool = False,
        project_id: Optional[str] = None
    ) -> GenerationConfig:
        """
        Determine the generation configuration based on feature flags, A/B testing, and request.
        """
        
        # Handle explicit mode requests
        if requested_mode == GenerationMode.CLASSIC:
            return self._get_classic_config()
        elif requested_mode == GenerationMode.ENHANCED:
            return self._get_enhanced_config(user_id)
        
        # Auto mode - determine based on feature flags and A/B testing
        return self._get_auto_config(user_id, is_iteration, project_id)
    
    def _get_classic_config(self) -> GenerationConfig:
        """Configuration for classic generation mode"""
        return GenerationConfig(
            mode=GenerationMode.CLASSIC,
            use_enhanced_prompts=False,
            use_context_analysis=False,
            use_user_patterns=False,
            use_hybrid_generation=False,
            use_ab_testing=False,
            use_metrics_tracking=True,  # Always track basic metrics
            ab_group="forced_classic"
        )
    
    def _get_enhanced_config(self, user_id: str) -> GenerationConfig:
        """Configuration for enhanced generation mode"""
        # Get A/B assignment for enhanced mode
        ab_assignment = self.enhanced_ab_manager.assign_user(user_id)
        
        return GenerationConfig(
            mode=GenerationMode.ENHANCED,
            use_enhanced_prompts=ab_assignment.features_enabled.get("enhanced_prompts", True),
            use_context_analysis=ab_assignment.features_enabled.get("context_analysis", True),
            use_user_patterns=ab_assignment.features_enabled.get("user_patterns", True),
            use_hybrid_generation=ab_assignment.features_enabled.get("hybrid_generation", True),
            use_ab_testing=True,
            use_metrics_tracking=True,
            ab_group=ab_assignment.group,
            features_enabled=ab_assignment.features_enabled,
            expected_improvement=ab_assignment.expected_improvement
        )
    
    def _get_auto_config(
        self, 
        user_id: str, 
        is_iteration: bool,
        project_id: Optional[str]
    ) -> GenerationConfig:
        """
        Auto-determine generation mode based on various factors.
        """
        
        # Check if user should be in enhanced mode based on various criteria
        should_use_enhanced = self._should_use_enhanced_mode(user_id, is_iteration, project_id)
        
        if should_use_enhanced:
            return self._get_enhanced_config(user_id)
        else:
            return self._get_classic_config()
    
    def _should_use_enhanced_mode(
        self, 
        user_id: str, 
        is_iteration: bool,
        project_id: Optional[str]
    ) -> bool:
        """
        Determine if a user should use enhanced mode based on various factors.
        """
        
        # Strategy 1: A/B testing assignment
        # All users are enrolled in A/B testing unless explicitly opted out
        ab_assignment = self.enhanced_ab_manager.assign_user(user_id)
        
        # If user is in control group, use classic mode
        if ab_assignment.group == "control_standard":
            return False
        
        # Strategy 2: Check for iterations
        # Iterations might benefit more from enhanced mode
        if is_iteration:
            # 80% of iterations go to enhanced mode for better context understanding
            user_hash = int(hashlib.md5(f"{user_id}_iteration".encode()).hexdigest(), 16)
            return (user_hash % 100) < 80
        
        # Strategy 3: Project-based routing
        if project_id:
            # Complex projects might benefit from enhanced mode
            # For now, use A/B assignment
            pass
        
        # Strategy 4: Global feature flags
        # Check if enhanced mode is globally enabled
        enhanced_mode_enabled = getattr(settings, 'ENABLE_ENHANCED_GENERATION', True)
        if not enhanced_mode_enabled:
            return False
        
        # Strategy 5: Load balancing
        # Ensure enhanced mode doesn't overwhelm the system
        enhanced_load_percentage = getattr(settings, 'ENHANCED_MODE_PERCENTAGE', 75)
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        
        # Use A/B assignment if within load percentage
        return (user_hash % 100) < enhanced_load_percentage
    
    def is_backwards_compatible_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Check if the request appears to be from a legacy client.
        """
        # Check for classic mode specific fields
        classic_fields = {"is_iteration", "parent_generation_id"}
        has_classic_fields = any(field in request_data for field in classic_fields)
        
        # Check for enhanced mode specific fields
        enhanced_fields = {"tech_stack", "domain", "constraints"}
        has_enhanced_fields = any(field in request_data for field in enhanced_fields)
        
        # Check for explicit generation_mode
        has_mode_specified = "generation_mode" in request_data
        
        # If has classic fields but no enhanced fields and no mode specified,
        # likely a legacy client
        return has_classic_fields and not has_enhanced_fields and not has_mode_specified
    
    def adapt_legacy_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapt a legacy request to the unified schema format.
        """
        adapted = request_data.copy()
        
        # Set default generation mode if not specified
        if "generation_mode" not in adapted:
            if self.is_backwards_compatible_request(request_data):
                adapted["generation_mode"] = GenerationMode.CLASSIC
            else:
                adapted["generation_mode"] = GenerationMode.AUTO
        
        # Ensure required fields have defaults
        if "context" not in adapted:
            adapted["context"] = {}
        
        if "constraints" not in adapted:
            adapted["constraints"] = []
        
        return adapted
    
    def get_streaming_config(self, generation_config: GenerationConfig) -> Dict[str, Any]:
        """Get configuration for streaming progress events"""
        return {
            "include_ab_metadata": generation_config.use_ab_testing,
            "include_enhanced_features": generation_config.mode == GenerationMode.ENHANCED,
            "detailed_progress": generation_config.use_metrics_tracking,
            "ab_group": generation_config.ab_group,
            "features_enabled": generation_config.features_enabled
        }


# Global instance
generation_feature_flag = GenerationFeatureFlag()
