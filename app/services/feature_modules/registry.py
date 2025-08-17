"""
Feature Module Registry

Imports and registers all available feature modules.
"""

from app.services.feature_modules import FeatureModule, FeatureModuleFactory

# Import all feature modules to register them
from app.services.feature_modules.auth_module import AuthFeatureModule
from app.services.feature_modules.file_upload_module import FileUploadFeatureModule  
from app.services.feature_modules.payments_module import PaymentsFeatureModule
from app.services.feature_modules.caching_module import CachingFeatureModule
from app.services.feature_modules.admin_dashboard_module import AdminDashboardFeatureModule

# Quick implementation of remaining modules
from typing import List, Optional, Dict, Any
from app.services.feature_modules import BaseFeatureModule

class RealTimeFeatureModule(BaseFeatureModule):
    """Real-time/WebSocket feature module"""
    
    def get_dependencies(self) -> List[str]:
        return ["websockets==12.0", "fastapi-websocket-pubsub==0.3.0"]
    
    def get_environment_vars(self) -> List[str]:
        return ["WEBSOCKET_URL", "PUBSUB_URL"]
    
    def generate_service_code(self) -> str:
        return '''"""WebSocket Service for real-time communication"""
from fastapi import WebSocket
from typing import List, Dict
import json

class WebSocketService:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

websocket_service = WebSocketService()
'''
    
    def generate_router_code(self) -> str:
        return '''"""WebSocket Router"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_service import websocket_service

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_service.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket_service.broadcast(f"Message: {data}")
    except WebSocketDisconnect:
        websocket_service.disconnect(websocket)
'''
    
    def generate_middleware_code(self) -> Optional[str]:
        return None
    
    def generate_schema_code(self) -> Optional[str]:
        return '''"""WebSocket Schemas"""
from pydantic import BaseModel

class WebSocketMessage(BaseModel):
    type: str
    data: dict
'''

class SearchFeatureModule(BaseFeatureModule):
    """Search feature module"""
    
    def get_dependencies(self) -> List[str]:
        return ["elasticsearch==8.11.0", "whoosh==2.7.4"]
    
    def get_environment_vars(self) -> List[str]:
        return ["ELASTICSEARCH_URL", "SEARCH_INDEX_NAME"]
    
    def generate_service_code(self) -> str:
        return '''"""Search Service"""
from elasticsearch import AsyncElasticsearch
from typing import List, Dict, Any

class SearchService:
    def __init__(self):
        self.es = AsyncElasticsearch([settings.ELASTICSEARCH_URL])
    
    async def search(self, query: str, index: str = None) -> List[Dict[str, Any]]:
        result = await self.es.search(
            index=index or settings.SEARCH_INDEX_NAME,
            body={"query": {"match": {"content": query}}}
        )
        return result["hits"]["hits"]
    
    async def index_document(self, doc_id: str, document: Dict[str, Any]):
        await self.es.index(
            index=settings.SEARCH_INDEX_NAME,
            id=doc_id,
            body=document
        )

search_service = SearchService()
'''
    
    def generate_router_code(self) -> str:
        return '''"""Search Router"""
from fastapi import APIRouter
from app.services.search_service import search_service

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/")
async def search(q: str, limit: int = 10):
    results = await search_service.search(q)
    return {"results": results[:limit]}
'''
    
    def generate_middleware_code(self) -> Optional[str]:
        return None
    
    def generate_schema_code(self) -> Optional[str]:
        return '''"""Search Schemas"""
from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    filters: dict = {}
'''

class NotificationsFeatureModule(BaseFeatureModule):
    """Notifications feature module"""
    
    def get_dependencies(self) -> List[str]:
        return ["emails==0.6", "twilio==8.10.0", "celery==5.3.4"]
    
    def get_environment_vars(self) -> List[str]:
        return ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "TWILIO_SID", "TWILIO_TOKEN"]
    
    def generate_service_code(self) -> str:
        return '''"""Notification Service"""
from emails import html
from twilio.rest import Client
from typing import List, Dict, Any

class NotificationService:
    def __init__(self):
        self.twilio_client = Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)
    
    async def send_email(self, to: str, subject: str, content: str):
        message = html(
            html=content,
            subject=subject,
            mail_from=settings.SMTP_USER
        )
        await message.send(to=to, smtp={
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "user": settings.SMTP_USER,
            "password": settings.SMTP_PASSWORD
        })
    
    async def send_sms(self, to: str, message: str):
        self.twilio_client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE,
            to=to
        )

notification_service = NotificationService()
'''
    
    def generate_router_code(self) -> str:
        return '''"""Notifications Router"""
from fastapi import APIRouter
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.post("/send-email")
async def send_email(to: str, subject: str, content: str):
    await notification_service.send_email(to, subject, content)
    return {"message": "Email sent successfully"}
'''
    
    def generate_middleware_code(self) -> Optional[str]:
        return None
    
    def generate_schema_code(self) -> Optional[str]:
        return '''"""Notification Schemas"""
from pydantic import BaseModel

class EmailRequest(BaseModel):
    to: str
    subject: str
    content: str
'''

# Register the remaining modules
FeatureModuleFactory.register(FeatureModule.REAL_TIME, RealTimeFeatureModule)
FeatureModuleFactory.register(FeatureModule.SEARCH, SearchFeatureModule)
FeatureModuleFactory.register(FeatureModule.NOTIFICATIONS, NotificationsFeatureModule)

def get_all_registered_modules():
    """Get all registered feature modules"""
    return {
        feature: FeatureModuleFactory.create(feature) 
        for feature in FeatureModuleFactory.get_all_features()
    }
