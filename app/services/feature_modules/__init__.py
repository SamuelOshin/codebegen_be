"""
Feature Modules for Advanced Template System

This module provides detailed implementations of feature modules
that can be composed into generated projects.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum


class FeatureModule(Enum):
    """Feature modules that can be included in generated projects"""
    AUTH = "auth"
    FILE_UPLOAD = "file_upload"
    REAL_TIME = "real_time"
    CACHING = "caching" 
    SEARCH = "search"
    PAYMENTS = "payments"
    NOTIFICATIONS = "notifications"
    ADMIN_DASHBOARD = "admin_dashboard"


class BaseFeatureModule(ABC):
    """
    Base class for feature modules.
    Each feature module provides code generation for specific functionality.
    """
    
    def __init__(self):
        self.name = self.__class__.__name__
        
    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """Return list of Python package dependencies"""
        pass
    
    @abstractmethod 
    def get_environment_vars(self) -> List[str]:
        """Return list of required environment variables"""
        pass
    
    @abstractmethod
    def generate_service_code(self) -> str:
        """Generate the main service implementation code"""
        pass
    
    @abstractmethod
    def generate_router_code(self) -> str:
        """Generate FastAPI router code for the feature"""
        pass
    
    @abstractmethod
    def generate_middleware_code(self) -> Optional[str]:
        """Generate middleware code if needed"""
        pass
    
    @abstractmethod
    def generate_schema_code(self) -> Optional[str]:
        """Generate Pydantic schemas for the feature"""
        pass
    
    def get_imports(self) -> List[str]:
        """Return list of common imports needed"""
        return [
            "from fastapi import APIRouter, Depends, HTTPException, status",
            "from pydantic import BaseModel",
            "from typing import Optional, List, Dict, Any"
        ]
    
    def get_endpoints(self) -> List[Dict[str, Any]]:
        """Return endpoint definitions for the feature"""
        return []
    
    def get_models(self) -> List[Dict[str, Any]]:
        """Return database model definitions if needed"""
        return []


class FeatureModuleFactory:
    """Factory for creating feature module instances"""
    
    _modules = {}
    
    @classmethod
    def register(cls, feature_type: FeatureModule, module_class):
        """Register a feature module implementation"""
        cls._modules[feature_type] = module_class
        
    @classmethod
    def create(cls, feature_type: FeatureModule) -> BaseFeatureModule:
        """Create a feature module instance"""
        if feature_type not in cls._modules:
            raise ValueError(f"Feature module {feature_type} not registered")
        return cls._modules[feature_type]()
    
    @classmethod
    def get_all_features(cls) -> List[FeatureModule]:
        """Get list of all available feature modules"""
        return list(cls._modules.keys())
