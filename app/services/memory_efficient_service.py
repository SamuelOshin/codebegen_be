"""
Memory-Efficient Generation Service

Integrates our hybrid memory-efficient approach with the existing advanced infrastructure.
This service serves as a memory-aware fallback for the existing AIOrchestrator.
"""

import asyncio
import psutil
from typing import Dict, Any, Optional, List
from loguru import logger

from app.services.advanced_template_system import AdvancedTemplateSystem, DomainType, FeatureModule, TemplateRequirements

logger = logger


class MemoryEfficientGenerationService:
    """
    Memory-efficient generation service that integrates with existing infrastructure
    as a fallback strategy when memory is insufficient for full AI models.
    """
    
    def __init__(self):
        self.template_system = AdvancedTemplateSystem()
        self.memory_threshold_mb = 4096  # 4GB minimum for local AI models
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the memory-efficient service"""
        try:
            logger.info("🚀 Initializing Memory-Efficient Generation Service...")
            
            # Check system memory
            memory_info = await self._analyze_memory()
            logger.info(f"💾 Available memory: {memory_info['available_mb']:,}MB")
            
            # Always initialize template system as it's lightweight
            logger.info("✅ Template-based generation ready")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize memory-efficient service: {e}")
            return False
    
    async def _analyze_memory(self) -> Dict[str, Any]:
        """Analyze current system memory"""
        memory = psutil.virtual_memory()
        return {
            "total_mb": memory.total // (1024 * 1024),
            "available_mb": memory.available // (1024 * 1024),
            "used_mb": memory.used // (1024 * 1024),
            "usage_percent": memory.percent,
            "can_load_ai_models": memory.available >= (self.memory_threshold_mb * 1024 * 1024)
        }
    
    async def can_use_ai_models(self) -> bool:
        """Check if there's enough memory for AI models"""
        memory_info = await self._analyze_memory()
        return memory_info["can_load_ai_models"]
    
    async def generate_project(
        self,
        prompt: str,
        tech_stack: str = "fastapi",
        domain: str = "general",
        features: Optional[List[str]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a project using memory-efficient templates
        
        Args:
            prompt: User requirements description
            tech_stack: Technology stack (fastapi, flask, django, etc.)
            domain: Domain type (ecommerce, fintech, etc.)
            features: List of features to include
            user_context: Additional user context for customization
        
        Returns:
            Dictionary containing generated files and metadata
        """
        try:
            logger.info(f"🎯 Generating project with memory-efficient approach")
            logger.info(f"   Tech Stack: {tech_stack}")
            logger.info(f"   Domain: {domain}")
            
            # Prepare template requirements
            requirements = self._prepare_template_requirements(
                prompt, tech_stack, domain, features or []
            )
            
            # Generate using advanced template system
            requirements_dict = {
                "tech_stack": tech_stack,
                "domain": domain,
                "features": features,
                "entities": requirements.entities,
                "complexity_level": requirements.complexity_level
            }
            
            result = self.template_system.generate_project(prompt, requirements_dict)
            
            # Add our metadata
            result.update({
                "strategy_used": "memory_efficient_template",
                "memory_info": await self._analyze_memory(),
                "generation_timestamp": asyncio.get_event_loop().time()
            })
            
            logger.info(f"✅ Generated {len(result.get('files', {})):,} files using memory-efficient templates")
            return result
            
        except Exception as e:
            logger.error(f"❌ Memory-efficient generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "strategy_used": "memory_efficient_template_failed"
            }
    
    def _prepare_template_requirements(
        self,
        prompt: str,
        tech_stack: str,
        domain: str,
        features: List[str]
    ) -> TemplateRequirements:
        """Prepare requirements for the advanced template system"""
        
        # Map domain string to enum
        domain_mapping = {
            "ecommerce": DomainType.ECOMMERCE,
            "content": DomainType.CONTENT_MGMT,
            "fintech": DomainType.FINTECH,
            "healthcare": DomainType.HEALTHCARE,
            "general": DomainType.GENERAL
        }
        
        # Map features to enums
        feature_mapping = {
            "auth": FeatureModule.AUTH,
            "upload": FeatureModule.FILE_UPLOAD,
            "realtime": FeatureModule.REAL_TIME,
            "cache": FeatureModule.CACHING,
            "search": FeatureModule.SEARCH,
            "payments": FeatureModule.PAYMENTS,
            "notifications": FeatureModule.NOTIFICATIONS,
            "admin": FeatureModule.ADMIN_DASHBOARD
        }
        
        # Extract entities from prompt (simple keyword extraction)
        entities = self._extract_entities_from_prompt(prompt)
        
        # Determine complexity based on features and prompt length
        complexity = min(10, max(1, len(features) + len(prompt.split()) // 20))
        
        return TemplateRequirements(
            tech_stack=tech_stack,
            domain=domain_mapping.get(domain, DomainType.GENERAL),
            features=[feature_mapping[f] for f in features if f in feature_mapping],
            entities=entities,
            complexity_level=complexity
        )
    
    def _extract_entities_from_prompt(self, prompt: str) -> List[str]:
        """Extract potential entity names from the prompt"""
        # Simple keyword extraction for entity detection
        common_entities = [
            "user", "product", "order", "payment", "customer", "item", "post", 
            "comment", "article", "category", "tag", "invoice", "transaction",
            "account", "profile", "message", "notification", "file", "document"
        ]
        
        words = prompt.lower().split()
        entities = []
        
        for entity in common_entities:
            if entity in words or f"{entity}s" in words:
                entities.append(entity.capitalize())
        
        # Add custom entities mentioned in prompt
        import re
        # Look for patterns like "manage X" or "create X" 
        patterns = [
            r"manage (\w+)",
            r"create (\w+)",
            r"handle (\w+)",
            r"track (\w+)"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, prompt.lower())
            for match in matches:
                if match not in [e.lower() for e in entities]:
                    entities.append(match.capitalize())
        
        return entities[:5]  # Limit to 5 entities
    
    async def get_generation_strategies(self) -> Dict[str, Any]:
        """Get available generation strategies based on current system state"""
        memory_info = await self._analyze_memory()
        
        strategies = {
            "memory_efficient_template": {
                "available": True,
                "description": "Template-based generation for memory-constrained environments",
                "memory_required_mb": 50,
                "performance": "fast",
                "quality": "good"
            }
        }
        
        if memory_info["can_load_ai_models"]:
            strategies["local_ai_model"] = {
                "available": True,
                "description": "Local AI model generation (higher quality)",
                "memory_required_mb": 4096,
                "performance": "slower",
                "quality": "excellent"
            }
        else:
            strategies["local_ai_model"] = {
                "available": False,
                "description": f"Insufficient memory ({memory_info['available_mb']:,}MB < 4,096MB)",
                "memory_required_mb": 4096,
                "performance": "n/a",
                "quality": "n/a"
            }
        
        return {
            "memory_info": memory_info,
            "strategies": strategies,
            "recommended_strategy": "memory_efficient_template" if not memory_info["can_load_ai_models"] else "local_ai_model"
        }


# Create service instance
memory_efficient_service = MemoryEfficientGenerationService()


# Quick test templates for immediate use
QUICK_TEMPLATES = {
    "fastapi_basic": {
        "main.py": '''"""
FastAPI Application
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Generated API", version="1.0.0")

class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None

# In-memory storage (replace with database in production)
items_db = []
next_id = 1

@app.get("/")
async def root():
    return {"message": "Welcome to your generated API"}

@app.get("/items", response_model=List[Item])
async def get_items():
    return items_db

@app.post("/items", response_model=Item)
async def create_item(item: Item):
    global next_id
    item.id = next_id
    next_id += 1
    items_db.append(item)
    return item

@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
''',
        "requirements.txt": '''fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
''',
        "README.md": '''# Generated FastAPI Application

## Installation
```bash
pip install -r requirements.txt
```

## Run
```bash
python main.py
```

## API Documentation
Visit http://localhost:8000/docs for interactive API documentation.
'''
    },
    
    "flask_basic": {
        "app.py": '''"""
Flask Application
"""
from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# Simple JSON storage
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def home():
    return {"message": "Welcome to your generated Flask API"}

@app.route('/items', methods=['GET'])
def get_items():
    return jsonify(load_data())

@app.route('/items', methods=['POST'])
def create_item():
    data = load_data()
    item = request.json
    item['id'] = len(data) + 1
    data.append(item)
    save_data(data)
    return jsonify(item), 201

@app.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    data = load_data()
    for item in data:
        if item['id'] == item_id:
            return jsonify(item)
    return jsonify({"error": "Item not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
''',
        "requirements.txt": '''Flask==3.0.0
''',
        "README.md": '''# Generated Flask Application

## Installation
```bash
pip install -r requirements.txt
```

## Run
```bash
python app.py
```
'''
    }
}


async def quick_generate(framework: str = "fastapi") -> Dict[str, Any]:
    """Quick generation function for immediate testing"""
    template = QUICK_TEMPLATES.get(framework, QUICK_TEMPLATES["fastapi_basic"])
    
    return {
        "success": True,
        "files": template,
        "strategy_used": f"quick_template_{framework}",
        "memory_info": {
            "available_mb": psutil.virtual_memory().available // (1024 * 1024)
        }
    }
