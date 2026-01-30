# rag_dpr/dpr_analysis/query_builder.py
# This file implements the rule-based query generation logic.
# It maps DPR sections to specific, hardcoded guideline topics to
# create precise queries for the retriever, avoiding LLM hallucination.

def build_queries(dpr_sections: list[str]) -> dict[str, str]:
    """
    Generates hardcoded queries based on DPR section titles.
    This avoids using the LLM for query generation, which is unreliable
    for weak models.
    """
    query_map = {
        "Cost": "What are the cost estimates and do they align with CPWD cost norms?",
        "Technical": "Are the technical specifications compliant with the latest engineering standards?",
        "Timeline": "Is the project timeline realistic and does it include buffers for delays?",
        # Add more mappings as per compliance requirements
    }

    queries = {}
    for section in dpr_sections:
        if section in query_map:
            queries[section] = query_map[section]
    
    return queries

if __name__ == '__main__':
    # Example usage
    sections = ["Cost", "Timeline"]
    generated_queries = build_queries(sections)
    print(generated_queries)
