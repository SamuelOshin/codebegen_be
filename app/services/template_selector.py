from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from app.services.advanced_template_system import (
    AdvancedTemplateSystem, 
    DomainType, 
    FeatureModule,
    advanced_template_system
)

DOMAINS_DIR = Path(__file__).resolve().parents[2] / "configs" / "domains"


@dataclass
class TemplateDecision:
    base_template: str
    domain: Optional[str]
    features: List[str]
    rationale: str
    confidence: float = 0.0
    complexity_level: int = 5


class TemplateSelector:
    """
    Enhanced template selector that integrates with Advanced Template System
    for intelligent, parameterized template selection.
    """
    
    def __init__(self, domains_dir: Optional[Path] = None) -> None:
        self.domains_dir = domains_dir or DOMAINS_DIR
        self._domain_cache: Dict[str, Dict] = {}
        self.advanced_template_system = advanced_template_system
        
        # Enhanced complexity indicators
        self.complexity_indicators = {
            'high': [
                'microservices', 'distributed', 'scalable', 'enterprise',
                'machine learning', 'ai', 'real-time analytics', 'big data',
                'multi-tenant', 'high-availability', 'event-driven'
            ],
            'medium': [
                'authentication', 'payment', 'integration', 'api',
                'dashboard', 'admin', 'search', 'notifications',
                'user management', 'file upload', 'caching'
            ],
            'low': [
                'crud', 'basic', 'simple', 'minimal', 'prototype',
                'starter', 'demo', 'example'
            ]
        }

    def _load_domain(self, name: str) -> Optional[Dict]:
        path = self.domains_dir / f"{name}.yaml"
        if not path.exists():
            return None
        if name in self._domain_cache:
            return self._domain_cache[name]
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self._domain_cache[name] = data
        return data

    def detect_domain(self, prompt: str) -> Optional[str]:
        """
        Enhanced domain detection using Advanced Template System.
        """
        # Use Advanced Template System for more sophisticated domain detection
        detected_domain = self.advanced_template_system.detect_domain(prompt)
        return detected_domain.value if detected_domain != DomainType.GENERAL else None

    def detect_features(self, prompt: str) -> List[str]:
        """
        Enhanced feature detection using Advanced Template System.
        """
        # Detect domain first to inform feature detection
        domain = self.advanced_template_system.detect_domain(prompt)
        
        # Use Advanced Template System for feature detection
        detected_features = self.advanced_template_system.detect_required_features(prompt, domain)
        
        return [feature.value for feature in detected_features]
    
    def calculate_complexity(self, prompt: str) -> int:
        """
        Calculate complexity level (1-10) based on prompt analysis.
        """
        prompt_lower = prompt.lower()
        
        high_score = sum(1 for indicator in self.complexity_indicators['high'] 
                        if indicator in prompt_lower)
        medium_score = sum(1 for indicator in self.complexity_indicators['medium'] 
                          if indicator in prompt_lower)
        low_score = sum(1 for indicator in self.complexity_indicators['low'] 
                       if indicator in prompt_lower)
        
        # Calculate weighted complexity score with priority to low complexity
        if low_score > 0 and high_score == 0:
            return max(1, min(4, 4 - low_score))  # Low: 1-4
        elif high_score > 0:
            return min(10, 7 + high_score)  # High: 7-10
        elif medium_score > 0:
            return min(7, 4 + medium_score)  # Medium: 4-7
        else:
            return 5  # Default medium complexity
    
    def select_optimal_template(
        self, 
        prompt: str, 
        user_history: Optional[List[Dict]] = None
    ) -> TemplateDecision:
        """
        Select optimal template using Advanced Template System with user history consideration.
        """
        # Use Advanced Template System for comprehensive analysis
        requirements = {
            "tech_stack": "fastapi_sqlalchemy",  # Default, could be inferred from prompt
            "entities": [],
            "features": self.detect_features(prompt)
        }
        
        # Generate project using Advanced Template System
        result = self.advanced_template_system.generate_project(prompt, requirements)
        
        template_info = result.get("template_info", {})
        
        # Build rationale
        rationale_parts = [
            f"Detected domain: {template_info.get('domain', 'general')}",
            f"Base template: {template_info.get('base_template', 'fastapi_basic')}",
            f"Features identified: {len(template_info.get('features', []))}",
            f"Entities: {len(template_info.get('entities', []))}"
        ]
        
        if user_history:
            rationale_parts.append(f"Considered {len(user_history)} previous projects")
        
        # Calculate confidence based on detection certainty
        domain = template_info.get('domain', 'general')
        features = template_info.get('features', [])
        
        confidence = 0.5  # Base confidence
        if domain != 'general':
            confidence += 0.3  # Domain detected
        if features:
            confidence += min(0.2, len(features) * 0.05)  # Features detected
        
        complexity = self.calculate_complexity(prompt)
        
        return TemplateDecision(
            base_template=template_info.get('base_template', 'fastapi_basic'),
            domain=template_info.get('domain'),
            features=template_info.get('features', []),
            rationale=" | ".join(rationale_parts),
            confidence=round(confidence, 2),
            complexity_level=complexity
        )
        p = prompt.lower()
        if re.search(r"auth|login|jwt|oauth|rbac", p):
            features.append("auth")
        if re.search(r"upload|file|image|media", p):
            features.append("file_upload")
        if re.search(r"realtime|websocket|sse|live", p):
            features.append("real_time")
        if re.search(r"cache|redis", p):
            features.append("caching")
        if re.search(r"search|filter|fts|elasticsearch", p):
            features.append("search")
        return features

    def select_base_template(self, tech_stack: Optional[List[str]]) -> str:
        stack = [s.lower() for s in (tech_stack or [])]
        if "mongodb" in stack or "mongo" in stack:
            return "fastapi_mongo"
        return "fastapi_sqlalchemy"

    def decide(self, prompt: str, tech_stack: Optional[List[str]] = None) -> TemplateDecision:
        domain = self.detect_domain(prompt)
        features = self.detect_features(prompt)
        base = self.select_base_template(tech_stack)
        rationale = " | ".join([
            f"domain={domain or 'unknown'}",
            f"features={','.join(features) or 'none'}",
            f"base={base}",
        ])
        return TemplateDecision(
            base_template=base,
            domain=domain,
            features=features,
            rationale=rationale,
        )
