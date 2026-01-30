# rag_dpr/main.py
"""
RAG-DPR: Main entry point for DPR Compliance Analysis System.
"""
import os
import sys
from models.embeddings import EmbeddingsModel
from models.llm import SimpleLLM
from dpr_analysis.retriever import DPRRetriever


def main():
    print("=" * 70)
    print("  RAG-DPR: DPR Compliance Analysis System")
    print("=" * 70)
    
    # Initialize components
    print("\n[1/3] Initializing embedding model (GPU)...")
    embedder = EmbeddingsModel()
    
    print("\n[2/3] Initializing retriever...")
    retriever = DPRRetriever(embedding_model=embedder)
    
    print("\n[3/3] Initializing LLM...")
    # Using local Ollama with smollm2:1.7b
    provider = "ollama"
    model = "smollm2:1.7b"
    
    try:
        llm = SimpleLLM(provider=provider, model=model)
    except Exception as e:
        print(f"LLM init failed: {e}")
        print("Continuing in retrieval-only mode")
        llm = None
    
    print("\n" + "=" * 70)
    print("System Ready! Enter queries ('quit' to exit)")
    print("=" * 70)
    
    while True:
        try:
            query = input("\nQuery: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
            
        if query.lower() in ['quit', 'exit', 'q']:
            break
        if not query:
            continue
        
        # Retrieve
        print("\nSearching...")
        results = retriever.retrieve(query, top_k=5)
        
        if not results:
            print("No relevant information found.")
            continue
        
        # Build context
        context = "\n\n---\n\n".join([
            f"Source: {r['source_file']}\n{r['text']}" 
            for r in results[:3]
        ])
        
        # Generate answer
        if llm:
            print("Generating answer...")
            answer = llm.generate(query, context=context)
            print("\n" + "-" * 70)
            print("ANSWER:", answer)
            print("-" * 70)
        else:
            print("\nRETRIEVED CONTEXT:")
            print(context[:800] + "..." if len(context) > 800 else context)
        
        print(f"\nSources:")
        for i, r in enumerate(results[:3]):
            print(f"  [{i+1}] {r['source_file']} (score: {r['score']:.3f})")


if __name__ == "__main__":
    main()
