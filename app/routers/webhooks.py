"""
Webhooks router for external service integrations.
"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/github")
async def github_webhook():
    """GitHub webhook handler (placeholder)"""
    return {"message": "GitHub webhook not implemented yet"}
