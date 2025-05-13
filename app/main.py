# app/main.py
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from pathlib import Path
import uvicorn
from typing import Dict, Any
import time
from datetime import datetime

from app.api.routes import router as api_router
from app.models.models import ErrorResponse
from app.config.settings import settings  # Add this import

# Enhanced logging configuration with colors
class ColorFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Configure logging with the custom formatter
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = ColorFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# Create FastAPI app
app = FastAPI(
    title="LinkedIn Job Recommender API",
    description="API for analyzing resumes and recommending LinkedIn job postings",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/ping")
def ping():
    return {"status": "ok"}

# Include API routes
app.include_router(api_router, prefix="/api")

# Custom exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            details=str(exc)
        ).dict(),
    )

@app.get("/")
async def root():
    return {
        "message": "LinkedIn Job Recommender API",
        "docs": "/docs",
        "health": "/api/health"
    }

# Create necessary directories
def setup_directories():
    # Create data directories
    Path("data/resumes").mkdir(parents=True, exist_ok=True)
    Path("data/jobs").mkdir(parents=True, exist_ok=True)
    logger.info("Created data directories")

# Enhanced startup message
if __name__ == "__main__":
    # Setup directories
    setup_directories()
    
    # Start the API server with enhanced logging
    host = settings.API_HOST
    port = settings.API_PORT
    
    logger.info("🚀 Starting LinkedIn Job Recommender API")
    logger.info(f"📡 Server: http://{host}:{port}")
    logger.info("📚 Documentation: http://localhost:8000/docs")
    logger.info("🔍 ReDoc: http://localhost:8000/redoc")
    logger.info("⚡ Development server is running...")
    
    uvicorn.run("app.main:app", host=host, port=port, reload=True)