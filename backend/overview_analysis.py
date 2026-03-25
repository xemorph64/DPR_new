import json
import logging
from typing import List, Dict, Any

from backend.config import settings
from backend.schemas import AnalysisReport, DynamicInsight
from backend.rag_service import document_rag

from groq import Groq

logger = logging.getLogger(__name__)

def generate_dynamic_overview(job_id: str, extracted_text: str, images: List[Dict[str, Any]] = []) -> AnalysisReport:
    """
    Generates a flexible, comprehensive overview of the DPR using RAG logic.
    Replaces the rigid 'run_rag_analysis_cloud'.
    """
    report = AnalysisReport(job_id=job_id, status="PROCESSING")
    
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY missing. Returning mock AnalysisReport.")
        report.executive_summary = "Mock executive summary. Please provide GROQ_API_KEY for real analysis."
        report.insights = [
            DynamicInsight(topic="Mock Topic", details="This is a mock insight.", risks=["Mock risk"])
        ]
        return report

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        model_name = settings.GROQ_MODEL_NAME
        
        # Step 1: Initial Skeleton / Executive Summary / Dynamic Topics
        # We pass the first 15000 chars roughly to get the lay of the land
        initial_context = extracted_text[:15000]
        prompt_1 = (
            "You are an expert infrastructure analyst reviewing a Detailed Project Report (DPR).\n"
            f"Based on the following extracted text, provide a JSON object containing two fields:\n"
            '1. "executive_summary": A high-level executive summary of what this project is about, its scale, and its primary objectives (under 3 paragraphs).\n'
            '2. "dynamic_topics": A list of 4 to 5 critical focus areas specifically tailored to this project based on the context (e.g., "Solar Panel Requirements", "Bridge Span Details", "Financial Estimates"). Do NOT formulate generic topics.\n\n'
            "Respond ONLY with a valid JSON object containing those two fields.\n\n"
            f"Extracted Text:\n{initial_context}"
        )
        
        res1 = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_1}],
            model=model_name,
            response_format={"type": "json_object"}
        )
        try:
            res1_json = json.loads(res1.choices[0].message.content.strip())
            exec_summary = res1_json.get("executive_summary", "Summary unavailable.")
            topics_to_explore = res1_json.get("dynamic_topics", [
                "Project Finances and Budget",
                "Technical Architecture",
                "Environmental Impact",
                "Potential Risks"
            ])
        except Exception as e:
            logger.error(f"Failed to parse initial dynamic topics JSON: {e}")
            exec_summary = "Could not generate executive summary."
            topics_to_explore = ["Key Aspects of the Project"]
             
        report.executive_summary = exec_summary
        
        # Step 2: Dynamic Insights via RAG
        insights = []
        for topic in topics_to_explore:
            # Query the personalized document RAG
            rag_chunks = document_rag.query_document(job_id, query=topic, limit=3)
            context_text = "\n\n".join([chunk.get("text", "") for chunk in rag_chunks]) if rag_chunks else "No specific sections found."
            
            prompt_2 = (
                f"You are analyzing a DPR. The user wants to know about: '{topic}'.\n"
                f"Here are the most relevant excerpts retrieved from the document:\n{context_text}\n\n"
                "Respond ONLY with a valid JSON object containing:\n"
                '{"details": "A 2-3 sentence summary of this topic based on the excerpts.", '
                '"risks": ["risk 1", "risk 2"], '
                '"extracted_values": {"Metric Name (e.g. Total Estimated Cost)": "Value (e.g. ₹500 Million)"} }\n'
                "For 'extracted_values', intelligently identify only the most critical quantifiable metrics (specific costs, capacities, exact numbers, dates) exactly related to this topic from the context."
            )
            
            res2 = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_2}],
                model=model_name,
                response_format={"type": "json_object"}
            )
            raw_json = res2.choices[0].message.content.strip()
                
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:-3].strip()
            if raw_json.startswith("```"):
                raw_json = raw_json[3:-3].strip()
            
            try:
                parsed = json.loads(raw_json)
                insights.append(DynamicInsight(
                    topic=topic,
                    details=parsed.get("details", "Unable to extract details."),
                    risks=parsed.get("risks", []),
                    extracted_values=parsed.get("extracted_values", {})
                ))
            except Exception as e:
                logger.error(f"Failed to parse JSON for topic {topic}: {e} from {raw_json}")
                
        report.insights = insights
        
        # Step 3: Final Synthesis (AI Assessment Report Card)
        from backend.schemas import EvaluationSummary
        
        synthesis_context = f"Executive Summary:\n{report.executive_summary}\n\nDetailed Insights:\n"
        for ins in insights:
            synthesis_context += f"Topic: {ins.topic}\nDetails: {ins.details}\nExtracted Metrics: {json.dumps(ins.extracted_values)}\nIdentified Risks: {json.dumps(ins.risks)}\n\n"
            
        prompt_3 = (
            "You are a Chief Infrastructure Assessor. Based ONLY on the following Executive Summary and Detailed Insights, "
            "generate a final, structured Evaluation Report Card for this Detailed Project Report (DPR). "
            "Identify the most critical gaps, flag the highest severity risks across ALL topics, and provide actionable recommendations for the human assessor to follow up on.\n\n"
            "Respond ONLY with a valid JSON object containing:\n"
            '{"flagged_risks": ["Risk 1", "Risk 2"], "missing_sections": ["Missing data 1", "Missing data 2"], "recommendations": ["Recommendation 1", "Recommendation 2"]}\n\n'
            f"Data to evaluate:\n{synthesis_context}"
        )
        
        try:
            res3 = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_3}],
                model=model_name,
                response_format={"type": "json_object"}
            )
            raw_eval_json = res3.choices[0].message.content.strip()
            
            if raw_eval_json.startswith("```json"):
                raw_eval_json = raw_eval_json[7:-3].strip()
            if raw_eval_json.startswith("```"):
                raw_eval_json = raw_eval_json[3:-3].strip()
                
            parsed_eval = json.loads(raw_eval_json)
            report.evaluation_summary = EvaluationSummary(
                flagged_risks=parsed_eval.get("flagged_risks", []),
                missing_sections=parsed_eval.get("missing_sections", []),
                recommendations=parsed_eval.get("recommendations", [])
            )
        except Exception as e:
            logger.error(f"Failed to generate evaluation summary: {e}")
            report.evaluation_summary = EvaluationSummary(flagged_risks=["Could not generate"], missing_sections=["Could not generate"], recommendations=["Could not generate"])

        # Step 4: Attach Images
        image_list = []
        for img in images:
            image_list.append({"path": img["path"], "caption": img.get("ref", "Extracted Chart/Image")})
        report.extracted_images = image_list
        
        report.status = "COMPLETED"
        return report

    except Exception as e:
        logger.error(f"Error generating dynamic overview: {str(e)}")
        if "quota" in str(e).lower() or "401" in str(e) or "403" in str(e):
            logger.warning("Groq API Error. Returning mock report for testing.")
            report.executive_summary = (
                "**Mock Executive Summary**\n\n"
                "The system successfully executed the PyMuPDF extraction, successfully indexed the chunks into Qdrant using embeddings, "
                "and triggered the Groq analysis endpoint. However, there was an API error.\n\n"
            )
            report.insights = [
                DynamicInsight(topic="Project Finances & ROI", details="The extraction and RAG pipeline queried for financial data successfully. (Mocked response due to API quota)", risks=["API Error"]),
                DynamicInsight(topic="Technical Architecture", details="The extraction isolated technical metrics. (Mocked response due to API quota)", risks=["API Error"])
            ]
            report.status = "COMPLETED"
            return report
            
        report.status = "FAILED"
        report.error_message = str(e)
        return report
