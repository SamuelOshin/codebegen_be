"""
Main entry point for the application
"""

import logging
import sys
import io

# Configure UTF-8 encoding for Windows console to support emojis
if sys.platform == 'win32':
    # Wrap stdout with UTF-8 encoding
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Configure logging to show in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)

# Set specific loggers to INFO level
logging.getLogger('app.services.llm_providers.gemini_provider').setLevel(logging.INFO)
logging.getLogger('app.services.ai_orchestrator').setLevel(logging.INFO)

from app.main import app

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info",
        access_log=True
    )
