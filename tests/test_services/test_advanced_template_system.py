"""
Tests for Phase 1: Template Enhancement - Advanced Template System
"""

import pytest
from app.services.advanced_template_system import (
    AdvancedTemplateSystem, 
    DomainType, 
    FeatureModule,
    advanced_template_system
)
from app.services.template_selector import TemplateSelector


class TestAdvancedTemplateSystem:
    """Test the Advanced Template System implementation"""
    
    def test_domain_detection_ecommerce(self):
        """Test domain detection for e-commerce prompts"""
        system = AdvancedTemplateSystem()
        
        ecommerce_prompts = [
            "I want to build an online store with products and shopping cart",
            "Create an e-commerce platform with inventory management",
            "Build a marketplace for buying and selling products"
        ]
        
        for prompt in ecommerce_prompts:
            domain = system.detect_domain(prompt)
            assert domain == DomainType.ECOMMERCE
    
    def test_domain_detection_fintech(self):
        """Test domain detection for fintech prompts"""
        system = AdvancedTemplateSystem()
        
        fintech_prompts = [
            "Build a banking API with account management",
            "Create a payment processing system with transactions",
            "I need a fintech app for investment tracking"
        ]
        
        for prompt in fintech_prompts:
            domain = system.detect_domain(prompt)
            assert domain == DomainType.FINTECH
    
    def test_domain_detection_healthcare(self):
        """Test domain detection for healthcare prompts"""
        system = AdvancedTemplateSystem()
        
        healthcare_prompts = [
            "Build a patient management system for a clinic",
            "Create a healthcare API with appointment scheduling",
            "I need a medical records management system"
        ]
        
        for prompt in healthcare_prompts:
            domain = system.detect_domain(prompt)
            assert domain == DomainType.HEALTHCARE
    
    def test_feature_detection(self):
        """Test feature detection from prompts"""
        system = AdvancedTemplateSystem()
        
        test_cases = [
            {
                "prompt": "Build an API with user authentication and file upload",
                "expected_features": [FeatureModule.AUTH, FeatureModule.FILE_UPLOAD]
            },
            {
                "prompt": "Create a real-time chat application with notifications",
                "expected_features": [FeatureModule.REAL_TIME, FeatureModule.NOTIFICATIONS]
            },
            {
                "prompt": "Build an e-commerce site with payment processing and admin dashboard",
                "expected_features": [FeatureModule.PAYMENTS, FeatureModule.ADMIN_DASHBOARD]
            }
        ]
        
        for test_case in test_cases:
            domain = system.detect_domain(test_case["prompt"])
            features = system.detect_required_features(test_case["prompt"], domain)
            
            for expected_feature in test_case["expected_features"]:
                assert expected_feature in features
    
    def test_base_template_selection(self):
        """Test base template selection logic"""
        system = AdvancedTemplateSystem()
        
        test_cases = [
            {"tech_stack": "fastapi_mongodb", "expected": "fastapi_mongo"},
            {"tech_stack": "fastapi_postgresql", "expected": "fastapi_sqlalchemy"},
            {"tech_stack": "fastapi_basic", "expected": "fastapi_basic"},
            {"tech_stack": "unknown", "expected": "fastapi_basic"}
        ]
        
        for test_case in test_cases:
            result = system.select_base_template(test_case["tech_stack"])
            assert result == test_case["expected"]
    
    def test_project_generation_ecommerce(self):
        """Test end-to-end project generation for e-commerce"""
        system = AdvancedTemplateSystem()
        
        prompt = "Build an e-commerce API with products, orders, and payment processing"
        requirements = {
            "tech_stack": "fastapi_sqlalchemy",
            "features": ["auth", "payments"],
            "entities": ["Product", "Order"]
        }
        
        result = system.generate_project(prompt, requirements)
        
        # Verify structure
        assert "files" in result
        assert "template_info" in result
        assert "dependencies" in result
        assert "environment_vars" in result
        
        # Verify domain detection
        assert result["template_info"]["domain"] == "ecommerce"
        
        # Verify features
        features = result["template_info"]["features"]
        assert "auth" in features
        assert "payments" in features
        
        # Verify generated files
        files = result["files"]
        assert "app/main.py" in files
        assert "requirements.txt" in files
        assert "README.md" in files
        
        # Verify entities
        entities = result["template_info"]["entities"]
        assert "Product" in entities
        assert "Order" in entities
    
    def test_project_generation_healthcare(self):
        """Test end-to-end project generation for healthcare"""
        system = AdvancedTemplateSystem()
        
        prompt = "Create a patient management system with appointment scheduling"
        requirements = {
            "tech_stack": "fastapi_sqlalchemy",
            "entities": ["Patient", "Appointment"]
        }
        
        result = system.generate_project(prompt, requirements)
        
        # Verify healthcare domain detection
        assert result["template_info"]["domain"] == "healthcare"
        
        # Verify healthcare-specific entities are included
        entities = result["template_info"]["entities"]
        assert "Patient" in entities
        assert "Appointment" in entities
        
        # Should include common healthcare entities from domain config
        # (Note: This depends on domain config being loaded)
    
    def test_template_composition(self):
        """Test template composition with domain config and features"""
        system = AdvancedTemplateSystem()
        
        # Mock domain config
        domain_config = system.get_domain_config(DomainType.ECOMMERCE)
        features = [FeatureModule.AUTH, FeatureModule.PAYMENTS]
        
        composition = system.compose_template(
            base_template="fastapi_sqlalchemy",
            domain_config=domain_config,
            features=features,
            custom_entities=["CustomEntity"]
        )
        
        # Verify composition structure
        assert composition["base_template"] == "fastapi_sqlalchemy"
        assert "entities" in composition
        assert "dependencies" in composition
        assert "environment_vars" in composition
        assert "endpoints" in composition
        
        # Verify feature dependencies are included
        dependencies = composition["dependencies"]
        assert any("jose" in dep for dep in dependencies)  # From auth feature
        assert any("stripe" in dep for dep in dependencies)  # From payments feature
        
        # Verify custom entity was added
        assert "CustomEntity" in composition["entities"]


class TestEnhancedTemplateSelector:
    """Test the enhanced template selector integration"""
    
    def test_template_selector_integration(self):
        """Test template selector with Advanced Template System"""
        selector = TemplateSelector()
        
        prompt = "Build an e-commerce API with user authentication and product management"
        
        decision = selector.select_optimal_template(prompt)
        
        # Verify decision structure
        assert decision.base_template in ["fastapi_basic", "fastapi_sqlalchemy", "fastapi_mongo"]
        assert decision.domain == "ecommerce"
        assert decision.confidence > 0.5  # Should have good confidence
        assert decision.complexity_level >= 1 and decision.complexity_level <= 10
        assert len(decision.rationale) > 0
    
    def test_complexity_calculation(self):
        """Test complexity calculation"""
        selector = TemplateSelector()
        
        test_cases = [
            {"prompt": "Simple CRUD API", "expected_range": (1, 4)},
            {"prompt": "API with authentication and payments", "expected_range": (4, 7)},
            {"prompt": "Distributed microservices with machine learning", "expected_range": (7, 10)}
        ]
        
        for test_case in test_cases:
            complexity = selector.calculate_complexity(test_case["prompt"])
            min_expected, max_expected = test_case["expected_range"]
            assert min_expected <= complexity <= max_expected
    
    def test_feature_detection_integration(self):
        """Test feature detection through template selector"""
        selector = TemplateSelector()
        
        prompt = "Build a real-time chat app with file uploads and user authentication"
        features = selector.detect_features(prompt)
        
        # Should detect multiple features
        assert "auth" in features
        assert "file_upload" in features
        assert "real_time" in features


# Integration test with actual prompt
def test_phase1_end_to_end():
    """
    End-to-end test of Phase 1 template enhancement implementation.
    This simulates the validation test scenario.
    """
    # Use the module-level instance
    system = advanced_template_system
    
    # Test prompt from validation test scenarios
    prompt = """
    I need to build an e-commerce platform with the following features:
    - Product catalog with categories
    - Shopping cart functionality
    - User authentication and registration
    - Order management system
    - Payment processing with Stripe
    - Admin dashboard for inventory management
    - Email notifications for order updates
    """
    
    requirements = {
        "tech_stack": "fastapi_postgresql",
        "features": ["auth", "payments", "admin_dashboard", "notifications"],
        "entities": ["Product", "Category", "Order", "User"]
    }
    
    # Generate project
    result = system.generate_project(prompt, requirements)
    
    # Validation checks for Phase 1 success criteria
    assert result is not None
    assert "files" in result
    assert len(result["files"]) > 5  # Should generate multiple files
    
    # Verify e-commerce domain detection
    assert result["template_info"]["domain"] == "ecommerce"
    
    # Verify feature detection
    features = result["template_info"]["features"]
    assert "auth" in features
    assert "payments" in features
    
    # Verify file generation
    files = result["files"]
    assert "app/main.py" in files
    assert "requirements.txt" in files
    assert "README.md" in files
    assert ".env.example" in files
    
    # Verify dependencies include domain-specific ones
    dependencies = result["dependencies"]
    assert any("stripe" in dep for dep in dependencies)
    
    # Verify environment variables
    env_vars = result["environment_vars"]
    assert "STRIPE_SECRET_KEY" in env_vars
    
    print("✅ Phase 1 Template Enhancement: End-to-end test passed!")
    print(f"📊 Generated {len(files)} files with {len(features)} features")
    print(f"🏗️ Base template: {result['template_info']['base_template']}")
    print(f"🎯 Domain: {result['template_info']['domain']}")
    print(f"⚡ Features: {', '.join(features)}")
