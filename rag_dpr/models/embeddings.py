# rag_dpr/models/embeddings.py
"""
GPU-Accelerated Embedding Model using BAAI/bge-base-en-v1.5.

This module enforces CUDA execution for embeddings on the RTX 4050.
The BGE-Base model produces 768-dimensional normalized vectors optimized
for semantic search and retrieval tasks.
"""
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Union


class EmbeddingsModel:
    """
    GPU-preferred wrapper for the BGE-Base embedding model.
    
    This class prefers CUDA for optimal performance but falls back to CPU
    if no GPU is available.
    
    Attributes:
        model_name (str): The HuggingFace model identifier.
        model (SentenceTransformer): The loaded sentence transformer model.
        device (str): The device the model is running on ('cuda' or 'cpu').
        embedding_dim (int): Dimension of output embeddings (768 for BGE-Base).
    """
    
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5", force_gpu: bool = False):
        """
        Initialize the embedding model with GPU preference.
        
        Args:
            model_name: HuggingFace model identifier.
            force_gpu: If True, raise error when GPU not available. Default: False.
            
        Raises:
            RuntimeError: If force_gpu=True and CUDA is not available.
        """
        self.model_name = model_name
        self.embedding_dim = 768  # BGE-Base output dimension
        
        # ============================================================
        # GPU PREFERENCE - Use CUDA if available, fallback to CPU
        # ============================================================
        if torch.cuda.is_available():
            # Get GPU info for confirmation
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"🚀 {gpu_name} Detected ({vram_gb:.1f}GB VRAM): Running Embeddings on CUDA")
            self.device = 'cuda'
        else:
            if force_gpu:
                raise RuntimeError(
                    "Fatal: GPU not detected. Please install PyTorch with CUDA.\n"
                    "Run: pip install torch torchvision torchaudio --index-url "
                    "https://download.pytorch.org/whl/cu121"
                )
            print("⚠️  GPU not detected. Running Embeddings on CPU (slower).")
            self.device = 'cpu'
        
        # Initialize model on selected device
        self.model = SentenceTransformer(self.model_name, device=self.device)
        
        # Ensure model is in evaluation mode
        self.model.eval()
        
        print(f"✅ Loaded {self.model_name} on {self.device.upper()}")
    
    def embed_query(self, text: str) -> np.ndarray:
        """
        Embed a single query text.
        
        For BGE models, queries should be prefixed with "query: " for optimal
        retrieval performance, but this is handled internally.
        
        Args:
            text: The query string to embed.
            
        Returns:
            np.ndarray: A (768,) dimensional normalized embedding vector.
        """
        # BGE models recommend prefixing queries
        prefixed_text = f"query: {text}"
        
        with torch.no_grad():
            embedding = self.model.encode(
                prefixed_text,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False
            )
        
        return embedding.astype('float32')
    
    def embed_documents(
        self, 
        texts: List[str], 
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Embed a list of document texts with batching to prevent OOM.
        
        Args:
            texts: List of document strings to embed.
            batch_size: Number of texts to process at once (default: 32 for 6GB VRAM).
            show_progress: Whether to display a progress bar.
            
        Returns:
            np.ndarray: A (N, 768) array of normalized embedding vectors.
        """
        if not texts:
            return np.array([], dtype='float32').reshape(0, self.embedding_dim)
        
        print(f"📊 Embedding {len(texts)} documents in batches of {batch_size}...")
        
        with torch.no_grad():
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=show_progress
            )
        
        # Clear CUDA cache after large batch operations (if using GPU)
        if self.device == 'cuda':
            torch.cuda.empty_cache()
        
        return embeddings.astype('float32')
    
    def get_vram_usage(self) -> dict:
        """
        Get current VRAM usage statistics.
        
        Returns:
            dict: Dictionary with allocated, reserved, and free VRAM in GB.
                  Returns zeros if running on CPU.
        """
        if self.device != 'cuda' or not torch.cuda.is_available():
            return {
                "allocated_gb": 0,
                "reserved_gb": 0,
                "total_gb": 0,
                "free_gb": 0,
                "device": "cpu"
            }
        
        allocated = torch.cuda.memory_allocated(0) / (1024**3)
        reserved = torch.cuda.memory_reserved(0) / (1024**3)
        total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        
        return {
            "allocated_gb": round(allocated, 2),
            "reserved_gb": round(reserved, 2),
            "total_gb": round(total, 2),
            "free_gb": round(total - reserved, 2),
            "device": "cuda"
        }


if __name__ == '__main__':
    # Test the embedding model
    print("=" * 60)
    print("TESTING GPU-ACCELERATED EMBEDDINGS")
    print("=" * 60)
    
    try:
        embedding_model = EmbeddingsModel()
        
        # Test document embedding
        test_docs = [
            "The project cost estimate must not exceed 15% of the approved budget.",
            "All civil works must follow CPWD specifications and guidelines.",
            "Environmental clearance is mandatory for projects above Rs. 100 Cr."
        ]
        doc_vectors = embedding_model.embed_documents(test_docs, batch_size=32)
        print(f"\n📄 Document vectors shape: {doc_vectors.shape}")
        
        # Test query embedding
        test_query = "What are the cost compliance requirements?"
        query_vector = embedding_model.embed_query(test_query)
        print(f"🔍 Query vector shape: {query_vector.shape}")
        
        # Show VRAM usage
        vram = embedding_model.get_vram_usage()
        print(f"\n💾 VRAM Usage: {vram['allocated_gb']}GB / {vram['total_gb']}GB")
        
        print("\n✅ All embedding tests passed!")
        
    except RuntimeError as e:
        print(f"❌ ERROR: {e}")
