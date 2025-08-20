#!/usr/bin/env python3
"""
Hybrid Qwen Generator for Limited Memory PCs
Combines multiple strategies: local small model + template fallback + API when available
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime


class HybridQwenGenerator:
    """
    Multi-strategy code generator optimized for limited memory:
    1. Try local Qwen-1.5B model (if memory allows)
    2. Fall back to intelligent templates
    3. Use HF API sparingly for complex requests
    """
    
    def __init__(self):
        self.local_generator = None
        self.hf_client = None
        self.strategy = "template"  # Default to most reliable
        self.memory_limit_mb = 4096  # 4GB limit for local model
        
    async def initialize(self):
        """Initialize with the best available strategy"""
        print("🚀 Initializing Hybrid Qwen Generator...")
        
        # Strategy 1: Try local model if memory allows
        try:
            from test_memory_efficient_qwen import MemoryEfficientQwenGenerator
            import psutil
            
            available_memory = psutil.virtual_memory().available // (1024 * 1024)  # MB
            print(f"💾 Available memory: {available_memory}MB")
            
            if available_memory > self.memory_limit_mb:
                print("🔄 Attempting to load local Qwen model...")
                self.local_generator = MemoryEfficientQwenGenerator()
                if await self.local_generator.initialize():
                    self.strategy = "local"
                    print("✅ Local model strategy activated")
                    return True
                else:
                    print("⚠️ Local model failed, falling back...")
            else:
                print(f"⚠️ Insufficient memory ({available_memory}MB < {self.memory_limit_mb}MB)")
                
        except Exception as e:
            print(f"⚠️ Local model unavailable: {e}")
        
        # Strategy 2: Try HF API (if token available and not rate limited)
        try:
            from app.core.config import settings
            if hasattr(settings, 'HF_TOKEN') and settings.HF_TOKEN:
                from huggingface_hub import InferenceClient
                self.hf_client = InferenceClient(api_key=settings.HF_TOKEN)
                self.strategy = "api"
                print("✅ HF API strategy activated")
                return True
        except Exception as e:
            print(f"⚠️ HF API unavailable: {e}")
        
        # Strategy 3: Template-based (always works)
        self.strategy = "template"
        print("✅ Template strategy activated (most reliable)")
        return True
    
    async def generate_project(self, requirements: str) -> Dict[str, Any]:
        """Generate project using the best available strategy"""
        print(f"🎯 Using strategy: {self.strategy}")
        
        if self.strategy == "local" and self.local_generator:
            return await self._generate_local(requirements)
        elif self.strategy == "api" and self.hf_client:
            return await self._generate_api(requirements)
        else:
            return await self._generate_template(requirements)
    
    async def _generate_local(self, requirements: str) -> Dict[str, Any]:
        """Generate using local Qwen model"""
        try:
            print("🔄 Generating with local Qwen model...")
            result = await self.local_generator.generate_project(requirements)
            result["strategy_used"] = "local_qwen_1.5b"
            return result
        except Exception as e:
            print(f"❌ Local generation failed: {e}")
            return await self._generate_template(requirements)
    
    async def _generate_api(self, requirements: str) -> Dict[str, Any]:
        """Generate using HF API (with rate limiting awareness)"""
        try:
            print("🔄 Generating with HuggingFace API...")
            
            prompt = f"""Generate a complete software project for: {requirements}

Return JSON format:
{{
    "files": [
        {{"path": "filename.py", "content": "code here"}}
    ],
    "dependencies": ["package1"],
    "setup_instructions": "setup steps"
}}"""

            # Use smaller model for API to conserve quota
            response = self.hf_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="Qwen/Qwen2.5-Coder-1.5B-Instruct",
                max_tokens=2048,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            result = self._parse_api_response(content, requirements)
            result["strategy_used"] = "hf_api"
            return result
            
        except Exception as e:
            print(f"❌ API generation failed (likely rate limited): {e}")
            return await self._generate_template(requirements)
    
    async def _generate_template(self, requirements: str) -> Dict[str, Any]:
        """Generate using intelligent templates (always works)"""
        print("🔄 Generating with intelligent templates...")
        
        # Analyze requirements to choose appropriate template
        req_lower = requirements.lower()
        
        if "fastapi" in req_lower or "api" in req_lower:
            return self._generate_fastapi_template(requirements)
        elif "flask" in req_lower:
            return self._generate_flask_template(requirements)
        elif "django" in req_lower:
            return self._generate_django_template(requirements)
        elif "crud" in req_lower or "database" in req_lower:
            return self._generate_crud_template(requirements)
        elif "web" in req_lower or "html" in req_lower:
            return self._generate_web_template(requirements)
        else:
            return self._generate_generic_template(requirements)
    
    def _generate_fastapi_template(self, requirements: str) -> Dict[str, Any]:
        """Generate FastAPI project template"""
        files = [
            {
                "path": "main.py",
                "content": '''"""
FastAPI application generated for: {requirements}
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Generated API", version="1.0.0")

# Pydantic models
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None

# In-memory storage (replace with database)
items_db = []
next_id = 1

@app.get("/")
async def root():
    return {{"message": "API for {requirements}"}}

@app.get("/items", response_model=List[Item])
async def get_items():
    return items_db

@app.post("/items", response_model=Item)
async def create_item(item: ItemCreate):
    global next_id
    new_item = Item(id=next_id, **item.dict())
    items_db.append(new_item)
    next_id += 1
    return new_item

@app.get("/items/{{item_id}}", response_model=Item)
async def get_item(item_id: int):
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.put("/items/{{item_id}}", response_model=Item)
async def update_item(item_id: int, item_update: ItemCreate):
    for i, item in enumerate(items_db):
        if item.id == item_id:
            items_db[i] = Item(id=item_id, **item_update.dict())
            return items_db[i]
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{{item_id}}")
async def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item.id == item_id:
            del items_db[i]
            return {{"message": "Item deleted"}}
    raise HTTPException(status_code=404, detail="Item not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''.format(requirements=requirements)
            },
            {
                "path": "requirements.txt",
                "content": """fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
"""
            },
            {
                "path": "README.md",
                "content": f"""# Generated FastAPI Project

## Requirements
{requirements}

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run the server: `python main.py`
3. Visit http://localhost:8000/docs for API documentation

## Features
- CRUD operations
- Automatic API documentation
- Pydantic data validation
- FastAPI best practices

Generated by CodebeGen Hybrid Generator
"""
            }
        ]
        
        return {
            "files": files,
            "dependencies": ["fastapi", "uvicorn", "pydantic"],
            "setup_instructions": "pip install -r requirements.txt && python main.py",
            "strategy_used": "template_fastapi"
        }
    
    def _generate_crud_template(self, requirements: str) -> Dict[str, Any]:
        """Generate CRUD application template"""
        files = [
            {
                "path": "crud_app.py",
                "content": f'''"""
CRUD Application for: {requirements}
"""
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

class DataStore:
    """Simple JSON-based data storage"""
    
    def __init__(self, filename: str = "data.json"):
        self.filename = filename
        self.data = self._load_data()
        self.next_id = max([item.get('id', 0) for item in self.data], default=0) + 1
    
    def _load_data(self) -> List[Dict]:
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                return json.load(f)
        return []
    
    def _save_data(self):
        with open(self.filename, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def create(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new item"""
        item['id'] = self.next_id
        item['created_at'] = datetime.now().isoformat()
        item['updated_at'] = datetime.now().isoformat()
        self.data.append(item)
        self.next_id += 1
        self._save_data()
        return item
    
    def read(self, item_id: Optional[int] = None) -> List[Dict] | Dict:
        """Read item(s)"""
        if item_id is None:
            return self.data
        
        for item in self.data:
            if item.get('id') == item_id:
                return item
        return None
    
    def update(self, item_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an item"""
        for i, item in enumerate(self.data):
            if item.get('id') == item_id:
                self.data[i].update(updates)
                self.data[i]['updated_at'] = datetime.now().isoformat()
                self._save_data()
                return self.data[i]
        return None
    
    def delete(self, item_id: int) -> bool:
        """Delete an item"""
        for i, item in enumerate(self.data):
            if item.get('id') == item_id:
                del self.data[i]
                self._save_data()
                return True
        return False

def main():
    """Demo usage"""
    store = DataStore("items.json")
    
    # Create
    item1 = store.create({{"name": "Example Item", "description": "This is a test item"}})
    print("Created:", item1)
    
    # Read all
    all_items = store.read()
    print("All items:", all_items)
    
    # Read one
    item = store.read(1)
    print("Item 1:", item)
    
    # Update
    updated = store.update(1, {{"name": "Updated Item"}})
    print("Updated:", updated)
    
    # Delete
    deleted = store.delete(1)
    print("Deleted:", deleted)

if __name__ == "__main__":
    main()
'''
            },
            {
                "path": "web_interface.py",
                "content": '''"""
Simple web interface for the CRUD application
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for
from crud_app import DataStore

app = Flask(__name__)
store = DataStore("web_data.json")

@app.route('/')
def index():
    items = store.read()
    return render_template('index.html', items=items)

@app.route('/api/items', methods=['GET', 'POST'])
def api_items():
    if request.method == 'GET':
        return jsonify(store.read())
    
    elif request.method == 'POST':
        data = request.get_json()
        item = store.create(data)
        return jsonify(item), 201

@app.route('/api/items/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
def api_item(item_id):
    if request.method == 'GET':
        item = store.read(item_id)
        if item:
            return jsonify(item)
        return jsonify({'error': 'Item not found'}), 404
    
    elif request.method == 'PUT':
        data = request.get_json()
        item = store.update(item_id, data)
        if item:
            return jsonify(item)
        return jsonify({'error': 'Item not found'}), 404
    
    elif request.method == 'DELETE':
        if store.delete(item_id):
            return jsonify({'message': 'Item deleted'})
        return jsonify({'error': 'Item not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
'''
            }
        ]
        
        return {
            "files": files,
            "dependencies": ["flask"],
            "setup_instructions": "pip install flask && python web_interface.py",
            "strategy_used": "template_crud"
        }
    
    def _generate_generic_template(self, requirements: str) -> Dict[str, Any]:
        """Generate generic Python application"""
        files = [
            {
                "path": "main.py",
                "content": f'''"""
Python Application for: {requirements}

This is a template application generated based on your requirements.
Customize this code to match your specific needs.
"""

def main():
    """Main application entry point"""
    print("Application for: {requirements}")
    print("=" * 50)
    
    # TODO: Implement your specific logic here
    # This template provides a starting structure
    
    # Example functionality based on requirements
    print("Starting application...")
    
    # Add your implementation here
    
    print("Application completed successfully!")

class Application:
    """Main application class"""
    
    def __init__(self):
        self.name = "Generated Application"
        self.requirements = "{requirements}"
    
    def run(self):
        """Run the application"""
        print(f"Running {{self.name}}")
        print(f"Requirements: {{self.requirements}}")
        
        # Implement your application logic
        self.process()
    
    def process(self):
        """Process the main application logic"""
        # TODO: Implement based on requirements
        pass

if __name__ == "__main__":
    app = Application()
    app.run()
    main()
'''
            },
            {
                "path": "utils.py",
                "content": '''"""
Utility functions for the application
"""
import json
import os
from typing import Any, Dict, List
from datetime import datetime

def save_json(data: Any, filename: str) -> bool:
    """Save data to JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        return False

def load_json(filename: str) -> Any:
    """Load data from JSON file"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return None

def log_message(message: str, level: str = "INFO"):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def validate_input(data: Dict, required_fields: List[str]) -> bool:
    """Validate that required fields are present"""
    for field in required_fields:
        if field not in data or data[field] is None:
            return False
    return True
'''
            }
        ]
        
        return {
            "files": files,
            "dependencies": [],
            "setup_instructions": "python main.py",
            "strategy_used": "template_generic"
        }
    
    def _parse_api_response(self, content: str, requirements: str) -> Dict[str, Any]:
        """Parse API response and extract project structure"""
        try:
            # Try to parse JSON
            import re
            json_match = re.search(r'\\{.*\\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback to template if parsing fails
        return self._generate_generic_template(requirements)


async def test_hybrid_generator():
    """Test the hybrid generator"""
    print("🧪 Testing Hybrid Qwen Generator")
    print("=" * 50)
    
    generator = HybridQwenGenerator()
    
    # Initialize
    await generator.initialize()
    
    # Test generation
    test_requirements = "Create a simple todo list manager with web interface"
    result = await generator.generate_project(test_requirements)
    
    print(f"\\n✅ Generation completed using: {result.get('strategy_used', 'unknown')}")
    print(f"📁 Files generated: {len(result['files'])}")
    print(f"📦 Dependencies: {result['dependencies']}")
    
    for file in result['files']:
        print(f"   📄 {file['path']}: {len(file['content'])} chars")
    
    return True


if __name__ == "__main__":
    asyncio.run(test_hybrid_generator())
