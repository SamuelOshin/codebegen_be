"""
Llama-3.1-8B model wrapper for schema extraction and entity parsing.
Handles prompt formatting, entity extraction, and relationship inference.
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: Transformers/PyTorch not available. Schema extraction will be limited.")

from app.core.config import settings


class LlamaParser:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.tokenizer = None
        self.model = None
        
        if TRANSFORMERS_AVAILABLE:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = "cpu"

    async def load(self):
        """Load Llama model for schema extraction"""
        if not TRANSFORMERS_AVAILABLE:
            print("Warning: Cannot load model - transformers not available")
            return
            
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model)

    def _load_model(self):
        """Synchronous model loading"""
        if not TRANSFORMERS_AVAILABLE:
            return
            
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, 
            trust_remote_code=True,
            use_fast=True
        )
        
        # Set pad token if not present
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            device_map="auto",
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        
        print(f"Loaded Llama parser model: {self.model_path}")

    async def extract_schema(
        self, 
        prompt: str, 
        domain: str = "general",
        tech_stack: str = "fastapi_postgres"
    ) -> Dict[str, Any]:
        """Extract database schema and API structure from natural language prompt"""
        
        if not TRANSFORMERS_AVAILABLE or not self.model:
            return self._extract_fallback_schema(prompt, domain, tech_stack)
        
        formatted_prompt = self._format_schema_prompt(prompt, domain, tech_stack)
        
        # Generate in thread pool
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, self._generate_schema, formatted_prompt)
        
        # Parse and validate output
        schema = self._parse_schema_output(output)
        return schema

    def _format_schema_prompt(self, prompt: str, domain: str, tech_stack: str) -> str:
        """Format prompt for schema extraction"""
        
        system_prompt = """You are an expert database architect and API designer. Your task is to analyze natural language requirements and extract a complete database schema and API structure.

You must output valid JSON with:
- entities: Database models with fields, types, and constraints
- relationships: Foreign keys and associations between entities
- endpoints: RESTful API endpoints with methods and descriptions
- constraints: Business rules and validation requirements

Output format:
{
  "entities": [
    {
      "name": "EntityName",
      "fields": [
        {"name": "field_name", "type": "string|integer|boolean|datetime|text", "constraints": ["required", "unique"], "description": "Field purpose"}
      ],
      "description": "Entity purpose"
    }
  ],
  "relationships": [
    {"from": "Entity1", "to": "Entity2", "type": "one-to-many|many-to-many|one-to-one", "foreign_key": "entity2_id"}
  ],
  "endpoints": [
    {"path": "/entities", "method": "GET|POST|PUT|DELETE", "description": "Endpoint purpose", "entity": "EntityName"}
  ],
  "constraints": ["Business rule descriptions"]
}"""

        domain_context = self._get_domain_context(domain)
        tech_context = self._get_tech_context(tech_stack)

        user_prompt = f"""### Requirements:
{prompt}

### Domain Context:
{domain_context}

### Technical Context:
{tech_context}

### Instructions:
Analyze the requirements and extract:
1. All entities (database models) with their fields and types
2. Relationships between entities
3. RESTful API endpoints needed
4. Business constraints and validation rules

Focus on creating a complete, normalized database schema that supports all the described functionality.

### Output:
Return valid JSON only, no additional text:"""

        return f"{system_prompt}\n\n{user_prompt}"

    def _get_domain_context(self, domain: str) -> str:
        """Get domain-specific context and common patterns"""
        domain_contexts = {
            "ecommerce": "Common entities: User, Product, Order, Category, Cart, Payment, Inventory, Review",
            "social_media": "Common entities: User, Post, Comment, Like, Follow, Message, Notification",
            "content_management": "Common entities: User, Article, Category, Tag, Comment, Media, Page",
            "task_management": "Common entities: User, Project, Task, Team, Comment, Attachment, Milestone",
            "fintech": "Common entities: User, Account, Transaction, Card, Payment, Invoice, Budget",
            "healthcare": "Common entities: Patient, Doctor, Appointment, Medical_Record, Prescription, Insurance",
            "general": "Common entities: User, Resource, Category, Relationship, Event, Setting"
        }
        return domain_contexts.get(domain, domain_contexts["general"])

    def _get_tech_context(self, tech_stack: str) -> str:
        """Get technology-specific considerations"""
        tech_contexts = {
            "fastapi_postgres": "Use PostgreSQL data types: VARCHAR, INTEGER, BOOLEAN, TIMESTAMP, TEXT, UUID, JSONB",
            "fastapi_sqlite": "Use SQLite-compatible types: TEXT, INTEGER, REAL, BLOB, NULL",
            "fastapi_mongo": "Use MongoDB document structure with embedded documents and references"
        }
        return tech_contexts.get(tech_stack, tech_contexts["fastapi_postgres"])

    def _generate_schema(self, prompt: str) -> str:
        """Synchronous schema generation"""
        inputs = self.tokenizer(
            prompt, 
            return_tensors="pt", 
            truncation=True, 
            max_length=4096
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=2048,
                temperature=0.1,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        generated = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:], 
            skip_special_tokens=True
        )
        
        return generated

    def _parse_schema_output(self, output: str) -> Dict[str, Any]:
        """Parse model output to extract schema dictionary"""
        try:
            # Find JSON in the output
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                schema = json.loads(json_str)
                
                # Validate and normalize schema
                return self._validate_schema(schema)
            else:
                # Fallback: try to extract entities manually
                return self._manual_schema_extraction(output)
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            return self._manual_schema_extraction(output)

    def _validate_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize extracted schema"""
        validated = {
            "entities": [],
            "relationships": [],
            "endpoints": [],
            "constraints": []
        }
        
        # Validate entities
        for entity in schema.get("entities", []):
            if isinstance(entity, dict) and "name" in entity:
                validated_entity = {
                    "name": entity["name"],
                    "fields": [],
                    "description": entity.get("description", "")
                }
                
                # Validate fields
                for field in entity.get("fields", []):
                    if isinstance(field, dict) and "name" in field and "type" in field:
                        validated_field = {
                            "name": field["name"],
                            "type": self._normalize_field_type(field["type"]),
                            "constraints": field.get("constraints", []),
                            "description": field.get("description", "")
                        }
                        validated_entity["fields"].append(validated_field)
                
                validated["entities"].append(validated_entity)
        
        # Validate relationships
        for rel in schema.get("relationships", []):
            if isinstance(rel, dict) and "from" in rel and "to" in rel:
                validated["relationships"].append({
                    "from": rel["from"],
                    "to": rel["to"],
                    "type": rel.get("type", "one-to-many"),
                    "foreign_key": rel.get("foreign_key", f"{rel['to'].lower()}_id")
                })
        
        # Validate endpoints
        for endpoint in schema.get("endpoints", []):
            if isinstance(endpoint, dict) and "path" in endpoint and "method" in endpoint:
                validated["endpoints"].append({
                    "path": endpoint["path"],
                    "method": endpoint["method"].upper(),
                    "description": endpoint.get("description", ""),
                    "entity": endpoint.get("entity", "")
                })
        
        # Validate constraints
        validated["constraints"] = [
            str(constraint) for constraint in schema.get("constraints", [])
            if constraint
        ]
        
        return validated

    def _normalize_field_type(self, field_type: str) -> str:
        """Normalize field types to standard SQLAlchemy types"""
        type_mapping = {
            "string": "String",
            "str": "String",
            "text": "Text",
            "integer": "Integer",
            "int": "Integer",
            "float": "Float",
            "decimal": "Decimal",
            "boolean": "Boolean",
            "bool": "Boolean",
            "datetime": "DateTime",
            "date": "Date",
            "time": "Time",
            "uuid": "UUID",
            "json": "JSON",
            "jsonb": "JSON"
        }
        return type_mapping.get(field_type.lower(), "String")

    def _manual_schema_extraction(self, output: str) -> Dict[str, Any]:
        """Fallback manual extraction if JSON parsing fails"""
        # Basic fallback schema
        return {
            "entities": [
                {
                    "name": "User",
                    "fields": [
                        {"name": "id", "type": "String", "constraints": ["primary_key"], "description": "User ID"},
                        {"name": "email", "type": "String", "constraints": ["unique", "required"], "description": "User email"},
                        {"name": "name", "type": "String", "constraints": ["required"], "description": "User name"},
                        {"name": "created_at", "type": "DateTime", "constraints": [], "description": "Creation timestamp"}
                    ],
                    "description": "User entity"
                }
            ],
            "relationships": [],
            "endpoints": [
                {"path": "/users", "method": "GET", "description": "List users", "entity": "User"},
                {"path": "/users", "method": "POST", "description": "Create user", "entity": "User"},
                {"path": "/users/{id}", "method": "GET", "description": "Get user", "entity": "User"}
            ],
            "constraints": ["Email must be unique", "Name is required"]
        }

    def _extract_fallback_schema(
        self, 
        prompt: str, 
        domain: str = "general",
        tech_stack: str = "fastapi_postgres"
    ) -> Dict[str, Any]:
        """Generate a basic schema when AI models are not available"""
        
        # Basic schema based on common patterns
        schema = {
            "entities": [
                {
                    "name": "User",
                    "fields": [
                        {"name": "id", "type": "integer", "primary_key": True},
                        {"name": "email", "type": "string", "unique": True, "nullable": False},
                        {"name": "name", "type": "string", "nullable": False},
                        {"name": "created_at", "type": "datetime", "nullable": False}
                    ],
                    "relationships": []
                }
            ],
            "endpoints": [
                {"path": "/users", "method": "GET", "description": "List users"},
                {"path": "/users", "method": "POST", "description": "Create user"},
                {"path": "/users/{id}", "method": "GET", "description": "Get user"},
                {"path": "/users/{id}", "method": "PUT", "description": "Update user"},
                {"path": "/users/{id}", "method": "DELETE", "description": "Delete user"},
            ],
            "tech_stack": {
                "database": "postgresql",
                "orm": "sqlalchemy",
                "framework": "fastapi",
                "auth": "jwt"
            },
            "domain": domain
        }
        
        # Try to extract entities from prompt keywords
        if "blog" in prompt.lower() or "post" in prompt.lower():
            schema["entities"].append({
                "name": "Post",
                "fields": [
                    {"name": "id", "type": "integer", "primary_key": True},
                    {"name": "title", "type": "string", "nullable": False},
                    {"name": "content", "type": "text", "nullable": False},
                    {"name": "user_id", "type": "integer", "foreign_key": "users.id"},
                    {"name": "created_at", "type": "datetime", "nullable": False}
                ],
                "relationships": [{"type": "belongs_to", "entity": "User"}]
            })
        
        return schema

    async def cleanup(self):
        """Cleanup model resources"""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        torch.cuda.empty_cache()
        print("Llama parser cleanup completed")
