# rag_dpr/ingest/chunker.py
"""
Implements the Clause-Aware Sliding Window chunking strategy.

This chunker is designed to respect the logical structure of legal and technical
documents by first splitting them along major sections (headers) and then by
clauses. For clauses that are too long for the model's context window, a
sliding window approach is used to create smaller, overlapping chunks.
"""
import re
from typing import List, Dict, Any

# A simple proxy for token counting. In a production environment,
# you would use the tokenizer from the actual embedding model.
# from transformers import AutoTokenizer
# tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-base-en-v1.5")
def count_tokens(text: str) -> int:
    """
    Approximates token count by splitting on spaces.
    Replace with a real tokenizer for production use.
    """
    return len(text.split())

def clause_aware_chunker(
    text: str,
    source_doc: str,
    max_tokens: int = 450,
    window_size: int = 400,
    overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    Chunks text based on a clause-aware sliding window strategy.

    Args:
        text (str): The full text of the document to be chunked.
        source_doc (str): The name of the source document for metadata.
        max_tokens (int): The maximum token limit for a single clause before
                          the sliding window is applied.
        window_size (int): The size of the sliding window in tokens.
        overlap (int): The number of tokens to overlap between windows.

    Returns:
        List[Dict[str, Any]]: A list of chunks, where each chunk is a
                              dictionary containing the text and metadata.
    """
    chunks = []
    
    # Step 1: Split by headers (e.g., "Section X", "Part A")
    # This regex is a placeholder and should be adapted to the specific DPR format.
    sections = re.split(r'(\n\s*Section \d+\.\d+ .*\n)', text, flags=re.IGNORECASE)
    
    current_section_title = "General"
    content_accumulator = ""

    def process_content(content: str, section_title: str, page_num: int):
        # Step 2: Split content by clause numbers (e.g., "1.1.1.", "a)")
        # This regex is also a placeholder.
        clauses = re.split(r'(\n\s*\d+\.\d+\.\d+\s+)', content)
        
        current_clause_id = "N/A"
        for i in range(0, len(clauses), 2):
            clause_text = clauses[i]
            if i + 1 < len(clauses):
                current_clause_id = clauses[i+1].strip()

            # Step 3: Check token count and apply sliding window if necessary
            if count_tokens(clause_text) > max_tokens:
                words = clause_text.split()
                for i in range(0, len(words), window_size - overlap):
                    window_words = words[i:i + window_size]
                    window_text = " ".join(window_words)
                    
                    chunks.append({
                        "text": window_text,
                        "metadata": {
                            "source_doc": source_doc,
                            "page_number": page_num, # Placeholder page number
                            "section_title": section_title,
                            "clause_id": f"{current_clause_id}-part{i//(window_size-overlap)+1}"
                        }
                    })
            elif clause_text.strip():
                chunks.append({
                    "text": clause_text.strip(),
                    "metadata": {
                        "source_doc": source_doc,
                        "page_number": page_num, # Placeholder page number
                        "section_title": section_title,
                        "clause_id": current_clause_id
                    }
                })

    for i in range(0, len(sections)):
        segment = sections[i]
        if re.match(r'(\n\s*Section \d+\.\d+ .*\n)', segment):
            # Process accumulated content before starting a new section
            process_content(content_accumulator, current_section_title, 1)
            content_accumulator = ""
            current_section_title = segment.strip()
        else:
            content_accumulator += segment
    
    # Process any remaining content
    process_content(content_accumulator, current_section_title, 1)

    return chunks

if __name__ == '__main__':
    # Example Usage
    sample_text = """
    Section 1.0 Introduction
    This is the introduction. It is quite short.

    Section 2.0 Technical Specifications
    2.1.1 This is the first clause of the technical specification. It details the requirements for material strength and durability.
    2.1.2 This is the second clause. It is a very long clause that will definitely need to be split by the sliding window. It discusses the power requirements, the voltage, the amperage, and the overall energy consumption of the primary machinery. It also goes into detail about the backup power systems, the required battery life, and the emergency protocols for power failure. The text just keeps going and going to simulate a very long legal or technical clause that exceeds the 450 token limit we have set. We need to ensure our sliding window chunker can handle this gracefully, creating overlapping chunks to maintain context. Let's add even more text to be absolutely sure. The quick brown fox jumps over the lazy dog. This is just filler text to increase the word count beyond the threshold. We need to be thorough in our testing to ensure the system is robust and reliable for government compliance tasks. This clause continues to describe the intricate details of the system's architecture, including the server specifications, the network topology, and the data storage solutions. It specifies the use of RAID 6 for data redundancy and requires off-site backups to be performed on a daily basis. The clause also mandates that all data must be encrypted both at rest and in transit using AES-256 encryption. This level of detail is common in government contracts and DPRs, making our clause-aware chunker a critical component of the RAG pipeline.

    Section 3.0 Budget
    3.1.1 The budget is allocated as per the CPWD norms.
    """
    
    document_chunks = clause_aware_chunker(sample_text, "DPR_Example_2026.pdf")
    
    for i, chunk in enumerate(document_chunks):
        print(f"--- Chunk {i+1} ---")
        print(f"Text: {chunk['text'][:100]}...")
        print(f"Metadata: {chunk['metadata']}")
        print()
