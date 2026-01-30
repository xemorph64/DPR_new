# rag_dpr/models/llm.py
"""
LLM interface supporting OpenAI API and Ollama for local inference.
"""
import os
import json
from typing import Optional


class SimpleLLM:
    """Simple LLM interface supporting OpenAI API or Ollama."""
    
    def __init__(self, provider: str = "openai", model: str = None):
        self.provider = provider.lower()
        
        if self.provider == "openai":
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY environment variable not set")
                self.client = openai.OpenAI(api_key=api_key)
                self.model = model or "gpt-3.5-turbo"
                print(f"LLM initialized: OpenAI {self.model}")
            except ImportError:
                raise ImportError("Install openai: pip install openai")
                
        elif self.provider == "ollama":
            self.api_url = "http://localhost:11434/api/generate"
            self.model = model or "llama2"
            print(f"LLM initialized: Ollama {self.model}")
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'ollama'")
    
    def generate(self, prompt: str, context: str = "", max_tokens: int = 500) -> str:
        if context:
            full_prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: {prompt}

Answer:"""
        else:
            full_prompt = prompt
        
        if self.provider == "openai":
            return self._openai_generate(full_prompt, max_tokens)
        elif self.provider == "ollama":
            return self._ollama_generate(full_prompt, max_tokens)
    
    def _openai_generate(self, prompt: str, max_tokens: int) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context. Be concise and accurate."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _ollama_generate(self, prompt: str, max_tokens: int) -> str:
        try:
            import requests
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": max_tokens}
                },
                timeout=120
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            return f"Error: {str(e)}. Is Ollama running? (ollama serve)"
