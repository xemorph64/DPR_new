"""
FastAPI backend for DPR Compliance Analysis System.
Serves the React Frontend and orchestrates OCR + RAG pipelines.
"""

import os
import sys
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import Optional

# Fix for Windows asyncio event loop policy
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.schemas import UploadResponse, StatusResponse, AnalysisReport
from backend.services import (
    process_dpr_file,
    get_job_status,
    initialize_ocr,
    initialize_rag,
)

# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="DPR Compliance Analysis API",
    description="Backend API for analyzing government DPR documents via OCR + RAG",
    version="1.0.0"
)

# ============================================================================
# CORS Configuration
# ============================================================================

# Allow React Frontend to access the API
ALLOWED_ORIGINS = [
    "http://localhost:3000",       # Local development
    "http://localhost:5173",       # Vite default port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    expose_headers=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Configuration
# ============================================================================

# Get root directory (parent of backend/)
ROOT_DIR = Path(__file__).parent.parent
UPLOADS_DIR = ROOT_DIR / "uploads"

# Ensure uploads directory exists
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Lifespan Events (Startup/Shutdown)
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Initialize ML models on application startup.
    This ensures models are loaded into VRAM before the first request.
    """
    import asyncio
    
    print("\n" + "=" * 70)
    print("[STARTUP] DPR Backend Startup - Initializing ML Models")
    print("=" * 70 + "\n")
    
    try:
        # Initialize OCR Pipeline
        print("[1/2] Loading OCR Pipeline (PaddleOCR + PyMuPDF)...")
        initialize_ocr()
        print("      [OK] OCR Pipeline ready\n")
        
        # Initialize RAG Components (defer to thread pool to avoid blocking)
        print("[2/2] Loading RAG Components (Embeddings + FAISS)...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, initialize_rag)
        print("      [OK] RAG Components ready\n")
        
        print("=" * 70)
        print("[OK] All models initialized successfully!")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR] STARTUP FAILED: {e}")
        print("Note: Ensure PaddleOCR and FAISS indices are properly installed")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on shutdown.
    """
    print("\n[SHUTDOWN] DPR Backend shutting down...")


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint for the API.
    """
    return {
        "status": "healthy",
        "service": "DPR Compliance Analysis API",
        "version": "1.0.0"
    }


# ============================================================================
# File Upload Endpoint
# ============================================================================

@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload a PDF file for DPR compliance analysis.
    
    - Saves the file to the uploads directory
    - Triggers background processing
    - Returns a job_id to track progress
    
    Args:
        file: PDF file to upload
        background_tasks: FastAPI background tasks
        
    Returns:
        UploadResponse with job_id
        
    Raises:
        HTTPException: If file is invalid or upload fails
    """
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())[:8].upper()
        
        # Create safe file path
        file_path = UPLOADS_DIR / f"{job_id}_{file.filename}"
        
        # Save uploaded file
        contents = await file.read()
        with open(file_path, 'wb') as f:
            f.write(contents)
        
        print(f"\n📁 File uploaded: {job_id} ({len(contents) / 1024:.1f} KB)")
        
        # Trigger background processing
        if background_tasks:
            background_tasks.add_task(
                process_dpr_file,
                job_id,
                str(file_path)
            )
            print(f"🔄 Background task started for job: {job_id}\n")
        
        return UploadResponse(job_id=job_id)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {str(e)}"
        )


# ============================================================================
# Status Check Endpoint
# ============================================================================

@app.get("/status/{job_id}", response_model=StatusResponse)
async def check_status(job_id: str):
    """
    Check the status of a DPR analysis job.
    
    Args:
        job_id: The job ID returned from /upload
        
    Returns:
        StatusResponse with current status and report (if completed)
        
    Raises:
        HTTPException: If job_id is not found
    """
    
    report = get_job_status(job_id)
    
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. Please upload a file first."
        )
    
    # If completed, return full report; otherwise just status
    return StatusResponse(
        job_id=job_id,
        status=report.status,
        report=report if report.status in ["COMPLETED", "FAILED"] else None
    )


# ============================================================================
# Report Endpoint (Get Full Report)
# ============================================================================

@app.get("/report/{job_id}", response_model=AnalysisReport)
async def get_report(job_id: str):
    """
    Retrieve the full analysis report for a completed job.
    
    Args:
        job_id: The job ID
        
    Returns:
        Full AnalysisReport
        
    Raises:
        HTTPException: If job not found or not completed
    """
    
    report = get_job_status(job_id)
    
    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found"
        )
    
    if report.status == "PROCESSING":
        raise HTTPException(
            status_code=202,  # Accepted - still processing
            detail="Job is still processing. Check status again later."
        )
    
    if report.status == "FAILED":
        raise HTTPException(
            status_code=400,
            detail=f"Job failed: {report.error_message}"
        )
    
    return report


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """
    API root endpoint with documentation links.
    """
    return {
        "message": "DPR Compliance Analysis API",
        "docs": "http://localhost:8000/docs",
        "redoc": "http://localhost:8000/redoc",
        "endpoints": {
            "health": "GET /health",
            "upload": "POST /upload",
            "status": "GET /status/{job_id}",
            "report": "GET /report/{job_id}"
        }
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )


# ============================================================================
# Run (Development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 70)
    print("🚀 Starting DPR Backend Server")
    print("=" * 70)
    print("📍 API URL: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("=" * 70 + "\n")
    
    # Note: Must run from ROOT directory for sys.path to work correctly
    # Run with: uvicorn backend.main:app --reload --port 8000
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
