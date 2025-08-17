"""
Template service for managing code generation templates.
Handles template loading, validation, and context preparation.
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.core.config import settings


class TemplateService:
    """Service for managing code generation templates"""
    
    def __init__(self):
        self.templates_dir = Path("templates")
        self.loaded_templates: Dict[str, Dict[str, Any]] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load all available templates from the templates directory"""
        if not self.templates_dir.exists():
            print(f"Templates directory not found: {self.templates_dir}")
            return
        
        for template_dir in self.templates_dir.iterdir():
            if template_dir.is_dir():
                template_config_path = template_dir / "template.yaml"
                if template_config_path.exists():
                    try:
                        with open(template_config_path, 'r', encoding='utf-8') as f:
                            template_config = yaml.safe_load(f)
                        
                        template_id = template_dir.name
                        template_config["id"] = template_id
                        template_config["path"] = str(template_dir)
                        
                        self.loaded_templates[template_id] = template_config
                        print(f"Loaded template: {template_id}")
                        
                    except Exception as e:
                        print(f"Error loading template {template_dir.name}: {e}")
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID"""
        return self.loaded_templates.get(template_id)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates"""
        return list(self.loaded_templates.values())
    
    def get_template_by_tech_stack(self, tech_stack: str) -> Optional[Dict[str, Any]]:
        """Get template by tech stack identifier"""
        for template in self.loaded_templates.values():
            if template.get("tech_stack") == tech_stack:
                return template
        return None
    
    def prepare_template_context(
        self, 
        template_id: str, 
        schema: Dict[str, Any], 
        generation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context for template rendering"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Extract entities and prepare model context
        entities = schema.get("entities", [])
        relationships = schema.get("relationships", [])
        endpoints = schema.get("endpoints", [])
        
        # Prepare model classes
        model_classes = []
        for entity in entities:
            model_class = {
                "name": entity["name"],
                "table_name": entity["name"].lower() + "s",
                "fields": [],
                "relationships": [],
                "description": entity.get("description", "")
            }
            
            # Process fields
            for field in entity.get("fields", []):
                field_info = {
                    "name": field["name"],
                    "type": self._map_field_type(field["type"], template.get("database", "postgresql")),
                    "constraints": field.get("constraints", []),
                    "description": field.get("description", ""),
                    "nullable": "required" not in field.get("constraints", []),
                    "unique": "unique" in field.get("constraints", []),
                    "primary_key": "primary_key" in field.get("constraints", [])
                }
                model_class["fields"].append(field_info)
            
            # Process relationships for this entity
            entity_relationships = [
                rel for rel in relationships 
                if rel.get("from") == entity["name"] or rel.get("to") == entity["name"]
            ]
            
            for rel in entity_relationships:
                if rel.get("from") == entity["name"]:
                    # This entity has a relationship to another
                    relationship_info = {
                        "type": "foreign_key",
                        "target": rel.get("to"),
                        "foreign_key": rel.get("foreign_key", f"{rel['to'].lower()}_id"),
                        "relationship_type": rel.get("type", "one-to-many")
                    }
                    model_class["relationships"].append(relationship_info)
            
            model_classes.append(model_class)
        
        # Prepare API endpoints
        api_endpoints = []
        for endpoint in endpoints:
            endpoint_info = {
                "path": endpoint["path"],
                "method": endpoint["method"],
                "description": endpoint.get("description", ""),
                "entity": endpoint.get("entity", ""),
                "function_name": self._generate_function_name(endpoint["method"], endpoint["path"]),
                "response_model": endpoint.get("entity", "dict")
            }
            api_endpoints.append(endpoint_info)
        
        # Template context
        context = {
            "template": template,
            "project_name": generation_context.get("project_name", "Generated API"),
            "description": generation_context.get("description", "Generated FastAPI application"),
            "domain": generation_context.get("domain", "general"),
            "tech_stack": template.get("tech_stack", "fastapi_postgres"),
            "database": template.get("database", "postgresql"),
            "has_auth": template.get("auth", False),
            "models": model_classes,
            "endpoints": api_endpoints,
            "dependencies": template.get("dependencies", []),
            "dev_dependencies": template.get("dev_dependencies", []),
            "features": template.get("features", [])
        }
        
        return context
    
    def _map_field_type(self, field_type: str, database: str) -> str:
        """Map generic field types to database-specific types"""
        type_mappings = {
            "postgresql": {
                "String": "String(255)",
                "Text": "Text",
                "Integer": "Integer",
                "Float": "Float",
                "Decimal": "Decimal(10, 2)",
                "Boolean": "Boolean",
                "DateTime": "DateTime",
                "Date": "Date",
                "Time": "Time",
                "UUID": "UUID",
                "JSON": "JSON"
            },
            "sqlite": {
                "String": "String(255)",
                "Text": "Text",
                "Integer": "Integer",
                "Float": "Float",
                "Decimal": "Float",  # SQLite doesn't have Decimal
                "Boolean": "Boolean",
                "DateTime": "DateTime",
                "Date": "Date",
                "Time": "Time",
                "UUID": "String(36)",  # UUID as string in SQLite
                "JSON": "Text"  # JSON as text in SQLite
            },
            "mongodb": {
                "String": "str",
                "Text": "str",
                "Integer": "int",
                "Float": "float",
                "Decimal": "float",
                "Boolean": "bool",
                "DateTime": "datetime",
                "Date": "date",
                "Time": "time",
                "UUID": "str",
                "JSON": "dict"
            }
        }
        
        mapping = type_mappings.get(database, type_mappings["postgresql"])
        return mapping.get(field_type, "String(255)")
    
    def _generate_function_name(self, method: str, path: str) -> str:
        """Generate function name from HTTP method and path"""
        # Remove path parameters and convert to snake_case
        clean_path = path.replace("{", "").replace("}", "").strip("/")
        path_parts = [part for part in clean_path.split("/") if part]
        
        method_lower = method.lower()
        
        if method_lower == "get":
            if len(path_parts) > 1:
                return f"get_{path_parts[-2]}"  # e.g., get_user for /users/{id}
            else:
                return f"list_{path_parts[0] if path_parts else 'items'}"
        elif method_lower == "post":
            return f"create_{path_parts[0] if path_parts else 'item'}"
        elif method_lower == "put":
            return f"update_{path_parts[0] if path_parts else 'item'}"
        elif method_lower == "delete":
            return f"delete_{path_parts[0] if path_parts else 'item'}"
        elif method_lower == "patch":
            return f"patch_{path_parts[0] if path_parts else 'item'}"
        else:
            return f"{method_lower}_{path_parts[0] if path_parts else 'item'}"
    
    def get_template_dependencies(self, template_id: str) -> Dict[str, List[str]]:
        """Get dependencies for a template"""
        template = self.get_template(template_id)
        if not template:
            return {"dependencies": [], "dev_dependencies": []}
        
        return {
            "dependencies": template.get("dependencies", []),
            "dev_dependencies": template.get("dev_dependencies", [])
        }


# Global template service instance
template_service = TemplateService()
