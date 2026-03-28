"""
PaperTrail Backend - Main FastAPI Application
Handwritten Government Form Digitisation System
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from datetime import datetime
from pathlib import Path

from .config import config
from .database import DatabaseManager
from .routes import upload_routes, verification_routes, records_routes, template_routes
from .routes.extraction_routes import router as extraction_router
from .models import HealthCheckResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print("\n" + "=" * 60)
    print("🚀 PaperTrail Backend Server Starting...")
    print("=" * 60)
    
    try:
        # Validate configuration
        config.validate_config()
        print("✓ Configuration validated")
        
        # Initialize database connection
        DatabaseManager.get_db_connection()
        print("✓ Database connection established")
        
        # Ensure upload folder exists
        os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
        print(f"✓ Upload folder ready: {config.UPLOAD_FOLDER}")
        
        print("=" * 60)
        print("✅ Server ready to accept requests")
        print(f"📡 PaperTrail backend running on http://127.0.0.1:8000")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"❌ Startup failed: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    print("\n" + "=" * 60)
    print("🛑 Shutting down PaperTrail Backend...")
    print("=" * 60)
    
    DatabaseManager.close_connection()
    print("✓ Database connection closed")
    
    print("=" * 60)
    print("👋 Server stopped")
    print("=" * 60 + "\n")


# Initialize FastAPI application
app = FastAPI(
    title="PaperTrail Backend API",
    description="Handwritten Government Form Digitisation System with OCR and AI",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Ensure upload directory exists before mounting
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# Include routers
app.include_router(upload_routes.router)
app.include_router(verification_routes.router)
app.include_router(records_routes.router)
app.include_router(template_routes.router)
app.include_router(extraction_router)       # coordinate-based field extraction

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_FOLDER), name="uploads")

# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend_static")


@app.get("/", tags=["root"])
async def root():
    """Serve frontend index.html."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
            "service": "PaperTrail Backend API",
            "version": "1.0.0",
            "description": "Handwritten Government Form Digitisation System",
            "endpoints": {
                "upload": "/api/upload-form",
                "extract_fields": "/api/extract-template-fields",
                "verify": "/api/verify-form",
                "records": "/api/forms",
                "health": "/health",
                "docs": "/docs"
            }
        }


@app.get("/health", response_model=HealthCheckResponse, tags=["monitoring"])
async def health_check():
    """
    Health check endpoint.
    Verifies database connection and system readiness.
    """
    try:
        # Check database connection
        db = DatabaseManager.get_db_connection()
        database_connected = True
        
        # Ping database
        db.command("ping")
        
    except Exception as e:
        database_connected = False
    
    # Check upload folder
    upload_folder_exists = os.path.exists(config.UPLOAD_FOLDER)
    
    status = "healthy" if (database_connected and upload_folder_exists) else "unhealthy"
    
    return HealthCheckResponse(
        status=status,
        timestamp=datetime.utcnow().isoformat(),
        database_connected=database_connected,
        upload_folder_exists=upload_folder_exists
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unhandled errors."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
