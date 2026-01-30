# rag_dpr/ingest/parse_pdf.py
"""
PDF Parsing Module.

This module handles extraction of text from PDF files. It uses pypdf for
digital/text-based PDFs, which is efficient and works well for most documents.
For scanned PDFs (OCR), you would need to add pytesseract + pdf2image.
"""
import os
from typing import Optional


def parse_pdf(file_path: str) -> str:
    """
    Parse a PDF file and extract all text content.
    
    Uses pypdf for text extraction from digital PDFs.
    
    Args:
        file_path: Path to the PDF file.
        
    Returns:
        str: Extracted text from all pages concatenated together.
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        Exception: If PDF parsing fails.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    print(f"Parsing PDF: {file_path}")
    
    try:
        # Try pypdf first (modern, maintained library)
        from pypdf import PdfReader
        
        reader = PdfReader(file_path)
        text_parts = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                # Add page marker for potential page-level chunking
                text_parts.append(f"\n--- Page {page_num} ---\n{page_text}")
        
        full_text = "\n".join(text_parts)
        print(f"   Extracted {len(full_text)} characters from {len(reader.pages)} pages")
        return full_text
        
    except ImportError:
        # Fallback to PyPDF2 if pypdf is not installed
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                text_parts = []
                
                for page_num, page in enumerate(reader.pages, start=1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"\n--- Page {page_num} ---\n{page_text}")
                
                full_text = "\n".join(text_parts)
                print(f"   Extracted {len(full_text)} characters from {len(reader.pages)} pages")
                return full_text
                
        except ImportError:
            raise ImportError(
                "No PDF parsing library found. Please install pypdf:\n"
                "  pip install pypdf\n"
                "Or PyPDF2:\n"
                "  pip install PyPDF2"
            )


if __name__ == '__main__':
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        text = parse_pdf(pdf_path)
        print(f"\n{'='*60}")
        print(f"Extracted Text (first 2000 chars):")
        print(f"{'='*60}")
        print(text[:2000])
    else:
        print("Usage: python parse_pdf.py <path_to_pdf>")
