# rag_dpr/ingest/clean_text.py
# This file is responsible for cleaning the raw text extracted from PDFs.
# This includes removing OCR errors, extra whitespace, and other noise
# to prepare the text for chunking and embedding.
# For now, it's a placeholder.

import re

def clean_text(text: str) -> str:
    """
    A placeholder for a text cleaning function.
    In a real implementation, this would involve more sophisticated
    noise removal techniques.
    """
    # Remove multiple newlines and spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

if __name__ == '__main__':
    # Example usage
    raw_text = "This  is an example   with extra   spacing and \n\n newlines."
    cleaned_text = clean_text(raw_text)
    print(cleaned_text)
