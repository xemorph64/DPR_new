# rag_dpr/dpr_analysis/retriever.py
"""
Retrieval module using FAISS for vector search and pickle for metadata.
"""
import os
import faiss
import pickle
import numpy as np
from typing import List, Dict, Any
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models.embeddings import EmbeddingsModel

STORE_PATH = os.path.join(os.path.dirname(__file__), '..', 'store')
FAISS_INDEX_PATH = os.path.join(STORE_PATH, "faiss.index")
METADATA_PATH = os.path.join(STORE_PATH, "metadata.pkl")


class DPRRetriever:
    """FAISS-based retriever with pickle metadata storage."""
    
    def __init__(self, embedding_model: EmbeddingsModel):
        """Initialize retriever with embedding model."""
        if not os.path.exists(FAISS_INDEX_PATH):
            raise FileNotFoundError(f"FAISS index not found. Run: python -m ingest.build_knowledge")
        if not os.path.exists(METADATA_PATH):
            raise FileNotFoundError(f"Metadata not found. Run: python -m ingest.build_knowledge")
        
        print("Loading FAISS index...")
        self.index = faiss.read_index(FAISS_INDEX_PATH)
        
        print("Loading metadata...")
        with open(METADATA_PATH, 'rb') as f:
            self.metadata = pickle.load(f)
        
        self.embedding_model = embedding_model
        print(f"Retriever ready: {self.index.ntotal} vectors, {len(self.metadata)} chunks")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top_k most relevant chunks for a query."""
        if self.index.ntotal == 0:
            return []

        query_vector = self.embedding_model.embed_query(query).reshape(1, -1)
        distances, indices = self.index.search(query_vector, min(top_k, self.index.ntotal))
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(self.metadata):
                continue
            chunk = self.metadata[idx]
            results.append({
                'text': chunk.get('text', ''),
                'metadata': chunk.get('metadata', {}),
                'source_file': chunk.get('source_file', 'Unknown'),
                'score': float(1 / (1 + dist))
            })
        return results


if __name__ == '__main__':
    embedder = EmbeddingsModel()
    retriever = DPRRetriever(embedder)
    results = retriever.retrieve("environmental clearance requirements", top_k=3)
    for i, r in enumerate(results):
        print(f"[{i+1}] {r['score']:.3f} | {r['source_file']}: {r['text'][:100]}...")
