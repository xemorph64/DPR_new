# rag_dpr/dpr_analysis/context_builder.py
# This file is responsible for assembling the retrieved chunks of text
# into a coherent context that can be passed to the LLM.
# For now, it's a placeholder.

def build_context(retrieved_chunks: list[dict]) -> str:
    """
    Assembles retrieved text chunks into a single context string for the LLM.
    """
    context = "\n---\n".join([chunk['text'] for chunk in retrieved_chunks])
    return context

if __name__ == '__main__':
    # Example usage
    chunks = [
        {'text': 'This is the first retrieved chunk.'},
        {'text': 'This is the second retrieved chunk.'}
    ]
    context_string = build_context(chunks)
    print(context_string)
