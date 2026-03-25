"""
Pydantic schemas for DPR compliance analysis API.
Defines the data structures for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class DynamicInsight(BaseModel):
    """Schema for a dynamically generated key insight."""
    topic: str = Field(..., description="The focus area of this insight")
    details: str = Field(..., description="Detailed narrative about this topic")
    risks: List[str] = Field(default_factory=list, description="Any risks associated with this topic")
    extracted_values: Dict[str, str] = Field(default_factory=dict, description="Key extracted numerical values and costs")


class EvaluationSummary(BaseModel):
    """Schema for final AI assessment report card."""
    flagged_risks: List[str] = Field(default_factory=list, description="High-severity risks aggregated from the document.")
    missing_sections: List[str] = Field(default_factory=list, description="Critical blind spots or missing data.")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations for the assessor.")


class AnalysisReport(BaseModel):
    """Complete dynamic analysis report schema."""
    
    job_id: str = Field(..., description="Unique identifier for the analysis job")
    status: str = Field(default="PROCESSING", description="Job status: PROCESSING, COMPLETED, or FAILED")
    
    # Flexible Overview Fields
    executive_summary: str = Field(default="", description="High-level narrative overview of the entire DPR")
    insights: List[DynamicInsight] = Field(default_factory=list, description="Key insights generated dynamically")
    evaluation_summary: Optional[EvaluationSummary] = Field(default=None, description="Final AI Assessment Report Card")
    extracted_images: List[Dict[str, str]] = Field(default_factory=list, description="List of relevant images extracted")
    
    error_message: Optional[str] = Field(default=None, description="Error details if status is FAILED")
    ocr_text: Optional[str] = Field(default=None, description="Raw extracted text from OCR (optional, for debugging)")
    processing_time: Optional[float] = Field(default=None, description="Time taken to process in seconds")


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
