# rag_dpr/dpr_analysis/evaluator.py
"""
Compliance Evaluator Module.

This module implements the ComplianceEvaluator class that uses the smollm2:1.7b
model via Ollama to compare DPR (Detailed Project Report) sections against
retrieved government guidelines and identify compliance discrepancies.

The evaluator enforces strict JSON output from the LLM to enable automated
parsing and downstream processing of compliance results.
"""
import json
import time
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


# ============================================================
# CONFIGURATION
# ============================================================
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "smollm2:1.7b"

# System prompt to constrain the weak LLM's behavior
SYSTEM_PROMPT = """You are a strict government compliance auditor. Your job is to compare a Project Proposal against Official Guidelines. You must output valid JSON only. Do not explain."""


@dataclass
class ComplianceResult:
    """
    Structured result from compliance evaluation.
    
    Attributes:
        status: Either "Compliant" or "Non-Compliant"
        issues: List of identified compliance issues (empty if compliant)
        raw_response: The raw LLM response for debugging
        model_used: Name of the LLM model used
        response_time: Time taken for LLM response in seconds
    """
    status: str
    issues: List[str]
    raw_response: str
    model_used: str
    response_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "status": self.status,
            "issues": self.issues,
            "raw_response": self.raw_response,
            "model_used": self.model_used,
            "response_time": self.response_time
        }


class ComplianceEvaluator:
    """
    Evaluates DPR sections against government guidelines using Ollama LLM.
    
    This class constructs carefully controlled prompts for the smollm2:1.7b
    model to perform compliance checking. It enforces JSON output format
    and handles parsing/validation of responses.
    
    Attributes:
        api_url: Ollama API endpoint URL.
        model_name: Name of the Ollama model to use.
        timeout: Request timeout in seconds.
    """
    
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        api_url: str = OLLAMA_API_URL,
        timeout: int = 120
    ):
        """
        Initialize the ComplianceEvaluator.
        
        Args:
            model_name: Ollama model name (default: smollm2:1.7b).
            api_url: Ollama API endpoint.
            timeout: Request timeout in seconds.
        """
        self.model_name = model_name
        self.api_url = api_url
        self.timeout = timeout
    
    def _build_prompt(
        self,
        dpr_text: str,
        retrieved_guidelines: str
    ) -> str:
        """
        Build the compliance evaluation prompt.
        
        Args:
            dpr_text: The DPR section text to evaluate.
            retrieved_guidelines: Retrieved guideline text for comparison.
            
        Returns:
            Formatted prompt string.
        """
        prompt = f"""OFFICIAL GUIDELINES:
{retrieved_guidelines}

PROJECT PROPOSAL:
{dpr_text}

TASK:
Identify any discrepancies.
Output Format: {{"status": "Compliant" | "Non-Compliant", "issues": ["issue 1", "issue 2"]}}"""
        
        return prompt
    
    def _call_ollama(
        self,
        prompt: str,
        system_prompt: str = SYSTEM_PROMPT
    ) -> Dict[str, Any]:
        """
        Call Ollama API with the given prompt.
        
        Args:
            prompt: The user prompt to send.
            system_prompt: The system prompt to constrain behavior.
            
        Returns:
            Dictionary with 'response' and 'response_time' keys.
            
        Raises:
            requests.RequestException: If API call fails.
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,  # Low temp for deterministic output
                "num_predict": 512,  # Limit output length
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }
        
        start_time = time.time()
        
        response = requests.post(
            self.api_url,
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        
        elapsed = time.time() - start_time
        
        result = response.json()
        
        return {
            "response": result.get("response", ""),
            "response_time": elapsed,
            "done": result.get("done", False),
            "total_duration": result.get("total_duration", 0)
        }
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse and validate the LLM's JSON response.
        
        Args:
            response_text: Raw response string from LLM.
            
        Returns:
            Parsed JSON as dictionary, or error dict if parsing fails.
        """
        try:
            # Try direct JSON parsing
            result = json.loads(response_text)
            
            # Validate required fields
            if "status" not in result:
                result["status"] = "Unknown"
            if "issues" not in result:
                result["issues"] = []
            
            # Normalize status value
            status = result["status"].lower()
            if "non" in status or "not" in status:
                result["status"] = "Non-Compliant"
            elif "compliant" in status:
                result["status"] = "Compliant"
            
            # Ensure issues is a list
            if isinstance(result["issues"], str):
                result["issues"] = [result["issues"]] if result["issues"] else []
            
            return result
            
        except json.JSONDecodeError as e:
            # Try to extract JSON from response if it contains extra text
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            return {
                "status": "Error",
                "issues": [f"Failed to parse LLM response: {str(e)}"],
                "parse_error": True
            }
    
    def evaluate_section(
        self,
        dpr_text: str,
        retrieved_guidelines: str
    ) -> ComplianceResult:
        """
        Evaluate a DPR section against retrieved guidelines.
        
        This is the main entry point for compliance evaluation. It constructs
        a prompt, calls the LLM, and parses the response into a structured
        ComplianceResult.
        
        Args:
            dpr_text: The DPR section text to evaluate.
            retrieved_guidelines: Retrieved guideline chunks for comparison.
            
        Returns:
            ComplianceResult with status, issues, and metadata.
        """
        # Build the prompt
        prompt = self._build_prompt(dpr_text, retrieved_guidelines)
        
        try:
            # Call Ollama API
            api_result = self._call_ollama(prompt)
            raw_response = api_result["response"]
            response_time = api_result["response_time"]
            
            # Parse the response
            parsed = self._parse_response(raw_response)
            
            return ComplianceResult(
                status=parsed.get("status", "Unknown"),
                issues=parsed.get("issues", []),
                raw_response=raw_response,
                model_used=self.model_name,
                response_time=response_time
            )
            
        except requests.exceptions.ConnectionError:
            return ComplianceResult(
                status="Error",
                issues=["Cannot connect to Ollama. Is it running? (ollama serve)"],
                raw_response="",
                model_used=self.model_name,
                response_time=0.0
            )
        except requests.exceptions.Timeout:
            return ComplianceResult(
                status="Error",
                issues=[f"Ollama request timed out after {self.timeout}s"],
                raw_response="",
                model_used=self.model_name,
                response_time=self.timeout
            )
        except Exception as e:
            return ComplianceResult(
                status="Error",
                issues=[f"Unexpected error: {str(e)}"],
                raw_response="",
                model_used=self.model_name,
                response_time=0.0
            )
    
    def batch_evaluate(
        self,
        sections: List[Dict[str, str]]
    ) -> List[ComplianceResult]:
        """
        Evaluate multiple DPR sections in batch.
        
        Args:
            sections: List of dicts with 'dpr_text' and 'guidelines' keys.
            
        Returns:
            List of ComplianceResult objects.
        """
        results = []
        
        for i, section in enumerate(sections):
            print(f"   Evaluating section {i+1}/{len(sections)}...")
            result = self.evaluate_section(
                dpr_text=section.get("dpr_text", ""),
                retrieved_guidelines=section.get("guidelines", "")
            )
            results.append(result)
        
        return results
    
    def check_ollama_status(self) -> bool:
        """
        Check if Ollama service is running and model is available.
        
        Returns:
            True if Ollama is ready, False otherwise.
        """
        try:
            # Check if Ollama is running
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5
            )
            response.raise_for_status()
            
            # Check if our model is available
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            return any(self.model_name in name for name in model_names)
            
        except Exception:
            return False


# Legacy function for backward compatibility
def evaluate_compliance(context: str, query: str) -> Dict[str, Any]:
    """
    Legacy wrapper function for backward compatibility.
    
    Args:
        context: The retrieved context/guidelines.
        query: The DPR text to evaluate.
        
    Returns:
        Dictionary with evaluation results.
    """
    evaluator = ComplianceEvaluator()
    result = evaluator.evaluate_section(
        dpr_text=query,
        retrieved_guidelines=context
    )
    return result.to_dict()


if __name__ == '__main__':
    print("=" * 70)
    print("🔍 COMPLIANCE EVALUATOR TEST")
    print("=" * 70)
    
    # Create evaluator instance
    evaluator = ComplianceEvaluator()
    
    # Check Ollama status
    print("\n📡 Checking Ollama status...")
    if not evaluator.check_ollama_status():
        print("❌ Ollama is not running or model not found.")
        print("   Run: ollama serve")
        print(f"   Then: ollama pull {MODEL_NAME}")
        exit(1)
    print(f"✅ Ollama ready with model: {MODEL_NAME}")
    
    # Test evaluation
    print("\n📝 Running test evaluation...")
    
    test_guidelines = """
    MDoNER Guidelines Section 4.2:
    - Project cost estimates must not exceed 15% variance from approved budget
    - All infrastructure projects require environmental clearance for amounts > Rs. 50 Cr
    - Detailed site surveys must be conducted within 6 months of project approval
    """
    
    test_dpr = """
    Project: New District Hospital Construction
    Estimated Cost: Rs. 85 Crores (20% above initial estimate of Rs. 71 Cr)
    Environmental Clearance: Pending
    Site Survey: Conducted 8 months after approval
    """
    
    result = evaluator.evaluate_section(
        dpr_text=test_dpr,
        retrieved_guidelines=test_guidelines
    )
    
    print(f"\n📊 Evaluation Result:")
    print(f"   Status:        {result.status}")
    print(f"   Issues Found:  {len(result.issues)}")
    for i, issue in enumerate(result.issues, 1):
        print(f"      {i}. {issue}")
    print(f"   Response Time: {result.response_time:.2f}s")
    print(f"   Model Used:    {result.model_used}")
    
    print("\n" + "=" * 70)
    print("✅ Evaluator test complete!")
    print("=" * 70)
