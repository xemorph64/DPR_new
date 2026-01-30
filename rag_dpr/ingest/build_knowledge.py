# rag_dpr/ingest/build_knowledge.py
"""
Knowledge Base Builder Script.

This script processes PDF documents from rag_dpr/data/guidelines/,
extracts and cleans text, chunks it intelligently, embeds the chunks
using GPU-accelerated BGE embeddings, and stores them in a FAISS index.

Optimized for RTX 4050 (6GB VRAM):
- Embeddings run on CUDA
- FAISS index runs on CPU (to conserve VRAM)
- Batch size of 32 to prevent OOM
"""
import os
import sys
import glob
import pickle
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

import faiss
import numpy as np

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.embeddings import EmbeddingsModel
from ingest.parse_pdf import parse_pdf
from ingest.clean_text import clean_text
from ingest.chunker import clause_aware_chunker


# ============================================================
# CONFIGURATION
# ============================================================
# Check both possible directory names (guidelines and guidlines typo)
GUIDELINES_DIR = PROJECT_ROOT / "data" / "guidlines"  # Using existing folder with typo
if not (PROJECT_ROOT / "data" / "guidlines").exists():
    GUIDELINES_DIR = PROJECT_ROOT / "data" / "guidelines"
STORE_DIR = PROJECT_ROOT / "store"
FAISS_INDEX_PATH = STORE_DIR / "faiss.index"
METADATA_PATH = STORE_DIR / "metadata.pkl"

# Embedding configuration (optimized for 6GB VRAM)
EMBEDDING_BATCH_SIZE = 32
EMBEDDING_DIM = 768  # BGE-Base dimension


def ensure_directories():
    """Ensure required directories exist."""
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    GUIDELINES_DIR.mkdir(parents=True, exist_ok=True)


def find_pdf_files() -> List[Path]:
    """
    Find all PDF files in the guidelines directory.
    
    Returns:
        List of Path objects pointing to PDF files.
    """
    pdf_pattern = str(GUIDELINES_DIR / "*.pdf")
    pdf_files = [Path(f) for f in glob.glob(pdf_pattern)]
    
    # Also check subdirectories
    pdf_pattern_recursive = str(GUIDELINES_DIR / "**" / "*.pdf")
    pdf_files.extend([Path(f) for f in glob.glob(pdf_pattern_recursive, recursive=True)])
    
    # Remove duplicates and sort
    pdf_files = sorted(set(pdf_files))
    
    return pdf_files


def process_single_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Process a single PDF: parse, clean, and chunk.
    
    Args:
        pdf_path: Path to the PDF file.
        
    Returns:
        List of chunk dictionaries with text and metadata.
    """
    print(f"\n📄 Processing: {pdf_path.name}")
    
    # Step 1: Parse PDF to extract raw text
    print("   ├─ Parsing PDF...")
    try:
        raw_text = parse_pdf(str(pdf_path))
        if not raw_text or len(raw_text.strip()) < 50:
            print(f"   └─ ⚠️  Warning: Very little text extracted from {pdf_path.name}")
            return []
    except Exception as e:
        print(f"   └─ ❌ Error parsing {pdf_path.name}: {e}")
        return []
    
    # Step 2: Clean the extracted text
    print("   ├─ Cleaning text...")
    cleaned_text = clean_text(raw_text)
    print(f"   │   └─ Cleaned: {len(raw_text)} → {len(cleaned_text)} chars")
    
    # Step 3: Chunk the cleaned text
    print("   ├─ Chunking text...")
    chunks = clause_aware_chunker(
        text=cleaned_text,
        source_doc=pdf_path.name,
        max_tokens=450,
        window_size=400,
        overlap=50
    )
    print(f"   └─ Created {len(chunks)} chunks")
    
    # Add source file metadata to each chunk
    for chunk in chunks:
        chunk['source_file'] = pdf_path.name
        chunk['source_path'] = str(pdf_path)
        chunk['processed_at'] = datetime.now().isoformat()
    
    return chunks


def build_faiss_index(
    embeddings: np.ndarray,
    use_gpu: bool = False
) -> faiss.Index:
    """
    Build a FAISS index from embeddings.
    
    Uses IndexFlatL2 on CPU to conserve GPU VRAM for the embedding model.
    For larger datasets (>100k vectors), consider using IndexIVFFlat.
    
    Args:
        embeddings: (N, 768) array of embedding vectors.
        use_gpu: Whether to place index on GPU (default: False to save VRAM).
        
    Returns:
        FAISS index with vectors added.
    """
    dim = embeddings.shape[1]
    
    # Use L2 distance (Euclidean) - works well with normalized vectors
    index = faiss.IndexFlatL2(dim)
    
    # Optionally move to GPU (not recommended for 6GB VRAM)
    if use_gpu and faiss.get_num_gpus() > 0:
        print("   └─ Moving FAISS index to GPU...")
        res = faiss.StandardGpuResources()
        index = faiss.index_cpu_to_gpu(res, 0, index)
    
    # Add vectors to index
    index.add(embeddings)
    
    return index


def save_knowledge_base(
    index: faiss.Index,
    metadata: List[Dict[str, Any]]
):
    """
    Save the FAISS index and metadata to disk.
    
    Args:
        index: The FAISS index to save.
        metadata: List of chunk metadata dictionaries.
    """
    # Ensure we have a CPU index for saving
    if hasattr(index, 'index'):  # GPU index wrapper
        cpu_index = faiss.index_gpu_to_cpu(index)
    else:
        cpu_index = index
    
    # Save FAISS index
    faiss.write_index(cpu_index, str(FAISS_INDEX_PATH))
    print(f"   ├─ Saved FAISS index: {FAISS_INDEX_PATH}")
    
    # Save metadata
    with open(METADATA_PATH, 'wb') as f:
        pickle.dump(metadata, f)
    print(f"   └─ Saved metadata: {METADATA_PATH}")


def load_knowledge_base() -> Tuple[faiss.Index, List[Dict[str, Any]]]:
    """
    Load existing FAISS index and metadata from disk.
    
    Returns:
        Tuple of (FAISS index, metadata list).
        
    Raises:
        FileNotFoundError: If index or metadata files don't exist.
    """
    if not FAISS_INDEX_PATH.exists():
        raise FileNotFoundError(f"FAISS index not found: {FAISS_INDEX_PATH}")
    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"Metadata not found: {METADATA_PATH}")
    
    index = faiss.read_index(str(FAISS_INDEX_PATH))
    
    with open(METADATA_PATH, 'rb') as f:
        metadata = pickle.load(f)
    
    return index, metadata


def main():
    """
    Main entry point for building the knowledge base.
    """
    print("=" * 70)
    print("🏗️  KNOWLEDGE BASE BUILDER")
    print("=" * 70)
    print(f"Guidelines Dir: {GUIDELINES_DIR}")
    print(f"Store Dir:      {STORE_DIR}")
    print("=" * 70)
    
    start_time = time.time()
    
    # Step 0: Ensure directories exist
    ensure_directories()
    
    # Step 1: Find all PDF files
    print("\n📂 STEP 1: Finding PDF files...")
    pdf_files = find_pdf_files()
    
    if not pdf_files:
        print("❌ No PDF files found in:", GUIDELINES_DIR)
        print("   Please place your guideline PDFs (MDoNER, CPWD) in this folder.")
        return
    
    print(f"   Found {len(pdf_files)} PDF file(s):")
    for pdf in pdf_files:
        print(f"   └─ {pdf.name}")
    
    # Step 2: Process each PDF
    print("\n📝 STEP 2: Processing PDFs (Parse → Clean → Chunk)...")
    all_chunks = []
    
    for pdf_path in pdf_files:
        chunks = process_single_pdf(pdf_path)
        all_chunks.extend(chunks)
    
    if not all_chunks:
        print("❌ No chunks generated from PDFs. Check your PDF files.")
        return
    
    print(f"\n   📊 Total chunks created: {len(all_chunks)}")
    
    # Step 3: Initialize GPU-accelerated embedding model
    print("\n🚀 STEP 3: Initializing GPU Embedding Model...")
    try:
        embedder = EmbeddingsModel()
    except RuntimeError as e:
        print(f"❌ Failed to initialize embeddings: {e}")
        return
    
    # Step 4: Embed all chunks
    print(f"\n🔢 STEP 4: Embedding {len(all_chunks)} chunks (batch_size={EMBEDDING_BATCH_SIZE})...")
    
    # Extract text from chunks
    chunk_texts = [chunk.get('text', chunk.get('content', '')) for chunk in all_chunks]
    
    # Embed with batching (prevents OOM on 6GB VRAM)
    embeddings = embedder.embed_documents(
        texts=chunk_texts,
        batch_size=EMBEDDING_BATCH_SIZE,
        show_progress=True
    )
    
    print(f"   └─ Embeddings shape: {embeddings.shape}")
    
    # Show VRAM usage after embedding
    vram = embedder.get_vram_usage()
    print(f"   └─ VRAM after embedding: {vram['allocated_gb']}GB / {vram['total_gb']}GB")
    
    # Step 5: Build FAISS index (on CPU to save VRAM)
    print("\n📇 STEP 5: Building FAISS index (on CPU)...")
    index = build_faiss_index(embeddings, use_gpu=False)
    print(f"   └─ Index contains {index.ntotal} vectors")
    
    # Step 6: Save to disk
    print("\n💾 STEP 6: Saving knowledge base to disk...")
    save_knowledge_base(index, all_chunks)
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print("✅ KNOWLEDGE BASE BUILT SUCCESSFULLY")
    print("=" * 70)
    print(f"   📄 PDFs processed:    {len(pdf_files)}")
    print(f"   📦 Total chunks:      {len(all_chunks)}")
    print(f"   🔢 Embedding dim:     {EMBEDDING_DIM}")
    print(f"   📇 Index vectors:     {index.ntotal}")
    print(f"   ⏱️  Time elapsed:      {elapsed:.1f}s")
    print(f"   💾 Index saved to:    {FAISS_INDEX_PATH}")
    print(f"   💾 Metadata saved to: {METADATA_PATH}")
    print("=" * 70)


if __name__ == '__main__':
    main()
