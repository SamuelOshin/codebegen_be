"""
Templates router for project template management endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user_optional
from app.schemas.generation import TemplateSearchRequest, TemplateSearchResponse
from app.schemas.user import UserResponse
from app.services.generation_file_service import template_search_service
from app.services.template_service import template_service

router = APIRouter()


@router.get(
    "/",
    summary="Get available templates",
    description="Get list of available project templates"
)
async def get_available_templates():
    """Get available project templates"""
    # Return templates from the TemplateService instance
    templates = template_service.list_templates()

    # Map internal template config to public-facing template info
    public_templates = []
    for t in templates:
        public_templates.append({
            "name": t.get("id") or t.get("name") or t.get("display_name"),
            "display_name": t.get("display_name") or t.get("name") or t.get("id"),
            "description": t.get("description", ""),
            "tech_stack": t.get("tech_stack", [])
        })

    return {"templates": public_templates}


@router.get(
    "/search",
    response_model=TemplateSearchResponse,
    summary="Search and filter templates",
    description="Search for templates based on criteria like domain, tech stack, etc."
)
async def search_templates(
    query: Optional[str] = Query(None, min_length=2, max_length=100, description="Search query"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    tech_stack: Optional[List[str]] = Query(None, description="Filter by tech stack"),
    complexity: Optional[str] = Query(None, description="Filter by complexity (low, medium, high)"),
    features: Optional[List[str]] = Query(None, description="Filter by features"),
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """Search and filter available templates"""
    search_request = TemplateSearchRequest(
        query=query,
        domain=domain,
        tech_stack=tech_stack,
        complexity=complexity,
        features=features
    )
    
    template_results = await template_search_service.search_templates(search_request)
    return template_results
