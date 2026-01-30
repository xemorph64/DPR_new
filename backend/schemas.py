"""
Pydantic schemas for DPR compliance analysis API.
Defines the data structures for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class DPRSection(BaseModel):
    """Schema for individual DPR compliance section."""
    
    status: str = Field(
        ..., 
        description="Compliance status: COMPLIANT, NON_COMPLIANT, or PARTIAL"
    )
    risks: List[str] = Field(
        default_factory=list,
        description="List of identified compliance risks or violations"
    )
    text_preview: str = Field(
        default="",
        description="Preview of relevant section text (first 500 chars)"
    )
    score: int = Field(
        default=0,
        description="Section-level compliance score (0-100)"
    )


class AnalysisReport(BaseModel):
    """Complete compliance analysis report schema."""
    
    job_id: str = Field(
        ...,
        description="Unique identifier for the analysis job"
    )
    status: str = Field(
        default="PROCESSING",
        description="Job status: PROCESSING, COMPLETED, or FAILED"
    )
    overall_score: int = Field(
        default=0,
        description="Overall compliance score (0-100)"
    )
    sections: Dict[str, DPRSection] = Field(
        default_factory=dict,
        description="Compliance scores by section (e.g., 'technical', 'environmental', 'administrative')"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if status is FAILED"
    )
    ocr_text: Optional[str] = Field(
        default=None,
        description="Raw extracted text from OCR (optional, for debugging)"
    )
    processing_time: Optional[float] = Field(
        default=None,
        description="Time taken to process in seconds"
    )


class UploadResponse(BaseModel):
    """Response when file is uploaded."""
    
    job_id: str = Field(
        ...,
        description="Job ID to track status"
    )
    message: str = Field(
        default="File uploaded successfully",
        description="Confirmation message"
    )


class StatusResponse(BaseModel):
    """Response when checking job status."""
    
    job_id: str = Field(..., description="Job ID")
    status: str = Field(..., description="Current job status")
    report: Optional[AnalysisReport] = Field(
        default=None,
        description="Full analysis report if status is COMPLETED"
    )


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(
        default=None,
        description="Additional error details"
    )
