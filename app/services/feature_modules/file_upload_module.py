"""
File Upload Feature Module

Provides secure file upload and management capabilities with
support for multiple file types, size validation, and storage.
"""

from typing import List, Optional, Dict, Any
from app.services.feature_modules import BaseFeatureModule, FeatureModule, FeatureModuleFactory


class FileUploadFeatureModule(BaseFeatureModule):
    """File upload feature module implementation"""
    
    def get_dependencies(self) -> List[str]:
        return [
            "aiofiles==23.2.0",
            "python-multipart==0.0.6",
            "python-magic==0.4.27",
            "pillow==10.0.1"
        ]
    
    def get_environment_vars(self) -> List[str]:
        return [
            "UPLOAD_DIR",
            "MAX_FILE_SIZE",
            "ALLOWED_EXTENSIONS",
            "UPLOAD_URL_PREFIX"
        ]
    
    def generate_service_code(self) -> str:
        return '''"""
File Upload Service

Handles file uploads, validation, storage, and retrieval.
"""

import os
import uuid
import aiofiles
import magic
from pathlib import Path
from typing import Optional, List, BinaryIO
from fastapi import UploadFile, HTTPException, status
from PIL import Image
from app.core.config import settings

class FileService:
    """Service for file upload and management"""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.max_file_size = settings.MAX_FILE_SIZE
        self.allowed_extensions = set(settings.ALLOWED_EXTENSIONS.split(","))
        self.upload_url_prefix = settings.UPLOAD_URL_PREFIX
        
        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, original_filename: str) -> str:
        """Generate unique filename while preserving extension"""
        file_ext = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{file_ext}"
    
    def _validate_file_type(self, file_content: bytes, filename: str) -> bool:
        """Validate file type using magic numbers and extension"""
        file_ext = Path(filename).suffix.lower()
        
        # Check extension
        if file_ext not in self.allowed_extensions:
            return False
        
        # Check MIME type using magic
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
            
            # Common safe MIME types
            allowed_mime_types = {
                '.jpg': ['image/jpeg'],
                '.jpeg': ['image/jpeg'],
                '.png': ['image/png'],
                '.gif': ['image/gif'],
                '.pdf': ['application/pdf'],
                '.txt': ['text/plain'],
                '.doc': ['application/msword'],
                '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
                '.csv': ['text/csv', 'application/csv']
            }
            
            if file_ext in allowed_mime_types:
                return mime_type in allowed_mime_types[file_ext]
                
        except Exception:
            return False
        
        return True
    
    def _validate_file_size(self, file_size: int) -> bool:
        """Validate file size"""
        return file_size <= self.max_file_size
    
    async def save_upload_file(self, upload_file: UploadFile) -> Dict[str, Any]:
        """Save uploaded file and return file info"""
        # Read file content
        content = await upload_file.read()
        
        # Validate file size
        if not self._validate_file_size(len(content)):
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {self.max_file_size} bytes"
            )
        
        # Validate file type
        if not self._validate_file_type(content, upload_file.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File type not allowed"
            )
        
        # Generate unique filename
        filename = self._generate_filename(upload_file.filename)
        file_path = self.upload_dir / filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Generate file info
        file_info = {
            "id": filename.split('.')[0],  # Use UUID part as ID
            "original_filename": upload_file.filename,
            "filename": filename,
            "size": len(content),
            "content_type": upload_file.content_type,
            "url": f"{self.upload_url_prefix}/{filename}"
        }
        
        # If it's an image, add dimensions
        if upload_file.content_type and upload_file.content_type.startswith('image/'):
            try:
                image = Image.open(file_path)
                file_info["width"] = image.width
                file_info["height"] = image.height
            except Exception:
                pass
        
        return file_info
    
    async def get_file_path(self, filename: str) -> Optional[Path]:
        """Get file path if exists"""
        file_path = self.upload_dir / filename
        if file_path.exists():
            return file_path
        return None
    
    async def delete_file(self, filename: str) -> bool:
        """Delete file from storage"""
        file_path = self.upload_dir / filename
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except Exception:
                return False
        return False
    
    async def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get file information"""
        file_path = await self.get_file_path(filename)
        if not file_path:
            return None
        
        stat = file_path.stat()
        return {
            "filename": filename,
            "size": stat.st_size,
            "created_at": stat.st_ctime,
            "modified_at": stat.st_mtime
        }

# Global file service instance
file_service = FileService()
'''
    
    def generate_router_code(self) -> str:
        return '''"""
File Upload Router

Provides endpoints for file upload, download, and management.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from typing import List
from app.services.file_service import file_service
from app.schemas.files import FileResponse, FileInfo

router = APIRouter(prefix="/files", tags=["files"])

@router.post("/upload", response_model=FileResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a single file"""
    try:
        file_info = await file_service.save_upload_file(file)
        return FileResponse(**file_info)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )

@router.post("/upload-multiple", response_model=List[FileResponse])
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """Upload multiple files"""
    if len(files) > 10:  # Limit to 10 files
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many files. Maximum 10 files allowed."
        )
    
    uploaded_files = []
    for file in files:
        try:
            file_info = await file_service.save_upload_file(file)
            uploaded_files.append(FileResponse(**file_info))
        except Exception as e:
            # Continue uploading other files
            continue
    
    if not uploaded_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were successfully uploaded"
        )
    
    return uploaded_files

@router.get("/download/{filename}")
async def download_file(filename: str):
    """Download file by filename"""
    file_path = await file_service.get_file_path(filename)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@router.get("/info/{filename}", response_model=FileInfo)
async def get_file_info(filename: str):
    """Get file information"""
    file_info = await file_service.get_file_info(filename)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return FileInfo(**file_info)

@router.delete("/delete/{filename}")
async def delete_file(filename: str):
    """Delete file"""
    success = await file_service.delete_file(filename)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or could not be deleted"
        )
    
    return {"message": "File deleted successfully"}
'''
    
    def generate_middleware_code(self) -> Optional[str]:
        return '''"""
File Upload Middleware

Provides middleware for file size validation and request processing.
"""

from fastapi import Request, HTTPException, status

class FileSizeMiddleware:
    """Middleware to check file size before processing"""
    
    def __init__(self, max_size: int = 10 * 1024 * 1024):  # 10MB default
        self.max_size = max_size
    
    async def __call__(self, request: Request, call_next):
        # Check content length for file uploads
        if request.method == "POST" and request.url.path.startswith("/files/"):
            content_length = request.headers.get("content-length")
            if content_length:
                if int(content_length) > self.max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request body too large. Maximum size: {self.max_size} bytes"
                    )
        
        return await call_next(request)
'''
    
    def generate_schema_code(self) -> Optional[str]:
        return '''"""
File Upload Schemas

Pydantic models for file upload requests and responses.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FileResponse(BaseModel):
    """File upload response schema"""
    id: str
    original_filename: str
    filename: str
    size: int
    content_type: Optional[str]
    url: str
    width: Optional[int] = None
    height: Optional[int] = None

class FileInfo(BaseModel):
    """File information schema"""
    filename: str
    size: int
    created_at: float
    modified_at: float

class FileUploadRequest(BaseModel):
    """File upload request schema"""
    description: Optional[str] = None
    tags: Optional[list] = None
'''
    
    def get_models(self) -> List[Dict[str, Any]]:
        return [{
            "name": "UploadedFile",
            "fields": [
                {"name": "id", "type": "String", "constraints": ["primary_key"]},
                {"name": "original_filename", "type": "String(255)", "constraints": ["required"]},
                {"name": "filename", "type": "String(255)", "constraints": ["required", "unique"]},
                {"name": "size", "type": "Integer", "constraints": ["required"]},
                {"name": "content_type", "type": "String(100)", "constraints": []},
                {"name": "url", "type": "String(500)", "constraints": ["required"]},
                {"name": "uploaded_by", "type": "String", "constraints": []},
                {"name": "created_at", "type": "DateTime", "constraints": []},
                {"name": "updated_at", "type": "DateTime", "constraints": []}
            ]
        }]
    
    def get_endpoints(self) -> List[Dict[str, Any]]:
        return [
            {"path": "/files/upload", "method": "POST", "description": "Upload single file"},
            {"path": "/files/upload-multiple", "method": "POST", "description": "Upload multiple files"},
            {"path": "/files/download/{filename}", "method": "GET", "description": "Download file"},
            {"path": "/files/info/{filename}", "method": "GET", "description": "Get file info"},
            {"path": "/files/delete/{filename}", "method": "DELETE", "description": "Delete file"}
        ]


# Register the module
FeatureModuleFactory.register(FeatureModule.FILE_UPLOAD, FileUploadFeatureModule)
