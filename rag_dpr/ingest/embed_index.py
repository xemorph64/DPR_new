# rag_dpr/ingest/embed_index.py
"""
Handles the embedding of text chunks and the creation/management of the
FAISS vector index and SQLite metadata store.

This script is designed to be run as part of the ingestion pipeline. It takes
chunks of text, generates embeddings using the configured model, and then
stores the embeddings in a FAISS index for fast retrieval. Crucially, it also
stores the associated metadata in a separate SQLite database, linking it to
the vectors by their index position.
"""
import os
import sqlite3
import numpy as np
import faiss
from typing import List, Dict, Any

# Assuming embeddings.py is in ../models/
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models.embeddings import BGEmbeddings

STORE_PATH = os.path.join(os.path.dirname(__file__), '..', 'store')
FAISS_INDEX_PATH = os.path.join(STORE_PATH, "dpr_index.faiss")
SQLITE_DB_PATH = os.path.join(STORE_PATH, "metadata.sqlite")

def create_stores_if_not_exist():
    """Creates the store directory and initializes the database if they don't exist."""
    if not os.path.exists(STORE_PATH):
        os.makedirs(STORE_PATH)
    
    if not os.path.exists(SQLITE_DB_PATH):
        print("Initializing SQLite database for metadata...")
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        # The table stores metadata as a JSON string for flexibility.
        # The id corresponds to the index of the vector in the FAISS store.
        cursor.execute("""
        CREATE TABLE metadata (
            id INTEGER PRIMARY KEY,
            source_doc TEXT NOT NULL,
            page_number INTEGER,
            section_title TEXT,
            clause_id TEXT,
            text TEXT NOT NULL
        )
        """)
        conn.commit()
        conn.close()

def index_documents(chunks: List[Dict[str, Any]], embedding_model: BGEmbeddings):
    """
    Generates embeddings for document chunks and saves them to FAISS and SQLite.

    Args:
        chunks (List[Dict[str, Any]]): A list of chunks from the chunker.
        embedding_model (BGEmbeddings): The embedding model wrapper.
    """
    create_stores_if_not_exist()
    
    texts_to_embed = [chunk['text'] for chunk in chunks]
    
    if not texts_to_embed:
        print("No new documents to index.")
        return

    print(f"Generating embeddings for {len(texts_to_embed)} chunks...")
    vectors = embedding_model.embed_documents(texts_to_embed)
    dimension = vectors.shape[1]

    # --- FAISS Indexing ---
    if os.path.exists(FAISS_INDEX_PATH):
        print("Loading existing FAISS index...")
        index = faiss.read_index(FAISS_INDEX_PATH)
    else:
        print("Creating new FAISS index...")
        # Using IndexFlatL2 as it's a simple, exact search index.
        # For larger datasets, a more complex index like IndexIVFFlat would be better.
        index = faiss.IndexFlatL2(dimension)

    start_index = index.ntotal
    index.add(vectors)
    print(f"Added {len(vectors)} vectors to FAISS index. Total vectors: {index.ntotal}")
    faiss.write_index(index, FAISS_INDEX_PATH)

    # --- SQLite Metadata Storage ---
    print("Storing metadata in SQLite...")
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    for i, chunk in enumerate(chunks):
        vector_id = start_index + i
        meta = chunk['metadata']
        cursor.execute(
            """
            INSERT INTO metadata (id, source_doc, page_number, section_title, clause_id, text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                vector_id,
                meta.get('source_doc'),
                meta.get('page_number'),
                meta.get('section_title'),
                meta.get('clause_id'),
                chunk['text']
            )
        )
    
    conn.commit()
    conn.close()
    print("Metadata storage complete.")

if __name__ == '__main__':
    # Example Usage
    # This would typically be run after the chunker.py script
    
    # 1. Initialize embedding model
    bge_model = BGEmbeddings()

    # 2. Create dummy chunks (as if from chunker.py)
    dummy_chunks = [
        {
            "text": "The project cost must not exceed $1 million as per guideline 4.2.",
            "metadata": {
                "source_doc": "DPR_A.pdf", "page_number": 10, 
                "section_title": "Budget", "clause_id": "4.2.1"
            }
        },
        {
            "text": "All construction materials must be certified by the national standards body.",
            "metadata": {
                "source_doc": "DPR_A.pdf", "page_number": 25,
                "section_title": "Technical Specs", "clause_id": "8.1.3"
            }
        }
    ]

    # 3. Index the documents
    index_documents(dummy_chunks, bge_model)
    
    # Verify
    if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(SQLITE_DB_PATH):
        print("\nVerification:")
        index = faiss.read_index(FAISS_INDEX_PATH)
        print(f"FAISS index contains {index.ntotal} vectors.")
        
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM metadata")
        count = cursor.fetchone()[0]
        print(f"SQLite database contains {count} metadata entries.")
        
        # Clean up dummy files for fresh runs
        os.remove(FAISS_INDEX_PATH)
        os.remove(SQLITE_DB_PATH)
        print("Cleaned up dummy index and metadata files.")
