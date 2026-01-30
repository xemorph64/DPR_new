# rag_dpr/check_hardware.py
"""
Hardware & Stack Sanity Check Script.

This script verifies that all components of the RAG-DPR stack are properly
configured and operational:
1. CUDA availability (RTX 4050)
2. VRAM capacity and usage
3. Embedding model loading and inference
4. Ollama service with smollm2:1.7b

Run this script before starting ingestion or analysis to ensure the
environment is correctly set up.
"""
import sys
import time
from typing import Tuple, Optional

# Colorama for colored output
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    # Fallback - no colors
    class Fore:
        GREEN = RED = YELLOW = CYAN = MAGENTA = WHITE = ""
        RESET = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""


def print_header(text: str):
    """Print a section header."""
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{text}")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")


def print_ok(text: str):
    """Print success message in green."""
    print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")


def print_fail(text: str):
    """Print failure message in red."""
    print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")


def print_warn(text: str):
    """Print warning message in yellow."""
    print(f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}")


def print_info(text: str):
    """Print info message in white."""
    print(f"{Fore.WHITE}ℹ️  {text}{Style.RESET_ALL}")


def check_cuda() -> Tuple[bool, dict]:
    """
    Check CUDA availability and GPU information.
    
    Returns:
        Tuple of (success, info_dict)
    """
    print_header("STEP 1: CUDA & GPU CHECK")
    
    try:
        import torch
    except ImportError:
        print_fail("PyTorch not installed!")
        print_info("Run: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        return False, {}
    
    info = {
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": None,
        "gpu_name": None,
        "vram_total_gb": None,
        "vram_used_gb": None,
        "vram_free_gb": None,
        "gpu_count": 0
    }
    
    print(f"   PyTorch Version: {info['torch_version']}")
    
    if not torch.cuda.is_available():
        print_fail("CUDA is NOT available!")
        print_info("Ensure you have installed PyTorch with CUDA support:")
        print_info("  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        return False, info
    
    print_ok("CUDA is available!")
    
    # Get detailed GPU info
    info["cuda_version"] = torch.version.cuda
    info["gpu_count"] = torch.cuda.device_count()
    
    print(f"   CUDA Version: {info['cuda_version']}")
    print(f"   GPU Count: {info['gpu_count']}")
    
    for i in range(info["gpu_count"]):
        props = torch.cuda.get_device_properties(i)
        gpu_name = props.name
        vram_total = props.total_memory / (1024**3)
        vram_used = torch.cuda.memory_allocated(i) / (1024**3)
        vram_reserved = torch.cuda.memory_reserved(i) / (1024**3)
        vram_free = vram_total - vram_reserved
        
        if i == 0:
            info["gpu_name"] = gpu_name
            info["vram_total_gb"] = round(vram_total, 2)
            info["vram_used_gb"] = round(vram_used, 2)
            info["vram_free_gb"] = round(vram_free, 2)
        
        print(f"\n   {Fore.MAGENTA}GPU {i}: {gpu_name}{Style.RESET_ALL}")
        print(f"   ├─ Total VRAM:    {vram_total:.2f} GB")
        print(f"   ├─ Allocated:     {vram_used:.2f} GB")
        print(f"   ├─ Reserved:      {vram_reserved:.2f} GB")
        print(f"   └─ Free:          {vram_free:.2f} GB")
    
    # Check if this looks like an RTX 4050
    if "4050" in info.get("gpu_name", ""):
        print_ok(f"RTX 4050 detected! Optimal for this project.")
    elif "RTX" in info.get("gpu_name", ""):
        print_ok(f"RTX GPU detected: {info['gpu_name']}")
    else:
        print_warn(f"GPU detected but not RTX series: {info['gpu_name']}")
    
    return True, info


def check_embedding_model() -> Tuple[bool, Optional[float]]:
    """
    Test loading and running the embedding model on GPU.
    
    Returns:
        Tuple of (success, inference_time_ms)
    """
    print_header("STEP 2: EMBEDDING MODEL CHECK")
    
    try:
        import torch
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print_fail(f"Required package not installed: {e}")
        print_info("Run: pip install sentence-transformers")
        return False, None
    
    model_name = "BAAI/bge-base-en-v1.5"
    print(f"   Loading model: {model_name}")
    print(f"   Device: CUDA")
    
    try:
        start_load = time.time()
        model = SentenceTransformer(model_name, device='cuda')
        load_time = time.time() - start_load
        print_ok(f"Model loaded in {load_time:.2f}s")
        
        # Run test inference
        test_text = "This is a test sentence for embedding."
        print(f"\n   Running test inference...")
        
        start_infer = time.time()
        with torch.no_grad():
            embedding = model.encode(test_text, normalize_embeddings=True)
        infer_time = (time.time() - start_infer) * 1000  # ms
        
        print_ok(f"Inference successful!")
        print(f"   ├─ Embedding dim: {embedding.shape}")
        print(f"   └─ Inference time: {infer_time:.2f}ms")
        
        # Check VRAM usage
        vram_used = torch.cuda.memory_allocated(0) / (1024**3)
        vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"\n   {Fore.CYAN}VRAM after loading model:{Style.RESET_ALL}")
        print(f"   └─ {vram_used:.2f}GB / {vram_total:.2f}GB ({(vram_used/vram_total)*100:.1f}%)")
        
        # Clean up
        del model
        torch.cuda.empty_cache()
        
        return True, infer_time
        
    except Exception as e:
        print_fail(f"Failed to load/run embedding model: {e}")
        return False, None


def check_ollama() -> Tuple[bool, Optional[float]]:
    """
    Test Ollama service and smollm2:1.7b model.
    
    Returns:
        Tuple of (success, response_time_s)
    """
    print_header("STEP 3: OLLAMA LLM CHECK")
    
    try:
        import requests
    except ImportError:
        print_fail("requests library not installed!")
        print_info("Run: pip install requests")
        return False, None
    
    ollama_url = "http://localhost:11434"
    model_name = "smollm2:1.7b"
    
    # Check if Ollama is running
    print(f"   Checking Ollama service at {ollama_url}...")
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        print_ok("Ollama service is running!")
    except requests.exceptions.ConnectionError:
        print_fail("Cannot connect to Ollama!")
        print_info("Start Ollama with: ollama serve")
        return False, None
    except Exception as e:
        print_fail(f"Error connecting to Ollama: {e}")
        return False, None
    
    # Check if model is available
    print(f"\n   Checking for model: {model_name}...")
    models = response.json().get("models", [])
    model_names = [m.get("name", "") for m in models]
    
    model_found = any(model_name in name for name in model_names)
    
    if not model_found:
        print_warn(f"Model {model_name} not found in Ollama!")
        print_info(f"Available models: {model_names}")
        print_info(f"Pull the model with: ollama pull {model_name}")
        return False, None
    
    print_ok(f"Model {model_name} is available!")
    
    # Test generation
    print(f"\n   Running test generation...")
    test_prompt = "Say 'Hello, RAG-DPR!' in JSON format: {\"message\": \"...\"}"
    
    payload = {
        "model": model_name,
        "prompt": test_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "num_predict": 50
        }
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{ollama_url}/api/generate",
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        elapsed = time.time() - start_time
        
        result = response.json()
        output = result.get("response", "")
        
        print_ok(f"Generation successful!")
        print(f"   ├─ Response time: {elapsed:.2f}s")
        print(f"   └─ Output: {output[:100]}{'...' if len(output) > 100 else ''}")
        
        return True, elapsed
        
    except requests.exceptions.Timeout:
        print_fail("Ollama request timed out!")
        print_info("The model might be loading. Try again in a moment.")
        return False, None
    except Exception as e:
        print_fail(f"Generation failed: {e}")
        return False, None


def check_dependencies() -> bool:
    """
    Check that all required Python packages are installed.
    
    Returns:
        True if all dependencies are present.
    """
    print_header("STEP 0: DEPENDENCY CHECK")
    
    required_packages = [
        ("torch", "PyTorch"),
        ("sentence_transformers", "Sentence Transformers"),
        ("faiss", "FAISS"),
        ("numpy", "NumPy"),
        ("requests", "Requests"),
    ]
    
    optional_packages = [
        ("colorama", "Colorama (colored output)"),
        ("pypdf", "PyPDF (PDF parsing)"),
        ("pdf2image", "PDF2Image (scanned PDFs)"),
    ]
    
    all_present = True
    
    print("   Required packages:")
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"   {Fore.GREEN}✓{Style.RESET_ALL} {name}")
        except ImportError:
            print(f"   {Fore.RED}✗{Style.RESET_ALL} {name} - NOT INSTALLED")
            all_present = False
    
    print("\n   Optional packages:")
    for package, name in optional_packages:
        try:
            __import__(package)
            print(f"   {Fore.GREEN}✓{Style.RESET_ALL} {name}")
        except ImportError:
            print(f"   {Fore.YELLOW}○{Style.RESET_ALL} {name} - not installed")
    
    if not all_present:
        print_fail("\nSome required packages are missing!")
        print_info("Install with: pip install torch sentence-transformers faiss-cpu numpy requests")
    else:
        print_ok("\nAll required packages are installed!")
    
    return all_present


def main():
    """
    Run all hardware and stack checks.
    """
    print(f"\n{Fore.CYAN}{Style.BRIGHT}")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║           RAG-DPR HARDWARE & STACK SANITY CHECK                      ║")
    print("║           Target: RTX 4050 (6GB) + smollm2:1.7b                       ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(Style.RESET_ALL)
    
    results = {
        "dependencies": False,
        "cuda": False,
        "embeddings": False,
        "ollama": False
    }
    
    # Step 0: Check dependencies
    results["dependencies"] = check_dependencies()
    if not results["dependencies"]:
        print_fail("\nCannot proceed without required dependencies.")
        sys.exit(1)
    
    # Step 1: Check CUDA
    results["cuda"], gpu_info = check_cuda()
    if not results["cuda"]:
        print_fail("\nCannot proceed without CUDA support.")
        sys.exit(1)
    
    # Step 2: Check embedding model
    results["embeddings"], embed_time = check_embedding_model()
    
    # Step 3: Check Ollama
    results["ollama"], ollama_time = check_ollama()
    
    # Final Summary
    print_header("FINAL SUMMARY")
    
    all_passed = all(results.values())
    
    print(f"\n   {'✅' if results['dependencies'] else '❌'} Dependencies:     {'PASS' if results['dependencies'] else 'FAIL'}")
    print(f"   {'✅' if results['cuda'] else '❌'} CUDA/GPU:          {'PASS' if results['cuda'] else 'FAIL'}")
    print(f"   {'✅' if results['embeddings'] else '❌'} Embedding Model:   {'PASS' if results['embeddings'] else 'FAIL'}")
    print(f"   {'✅' if results['ollama'] else '❌'} Ollama LLM:        {'PASS' if results['ollama'] else 'FAIL'}")
    
    if gpu_info:
        print(f"\n   {Fore.CYAN}Hardware:{Style.RESET_ALL}")
        print(f"   ├─ GPU: {gpu_info.get('gpu_name', 'Unknown')}")
        print(f"   └─ VRAM: {gpu_info.get('vram_total_gb', 0)} GB")
    
    print(f"\n{'='*70}")
    if all_passed:
        print(f"{Fore.GREEN}{Style.BRIGHT}🎉 ALL CHECKS PASSED! Your environment is ready.{Style.RESET_ALL}")
        print(f"\nNext steps:")
        print(f"   1. Place PDF guidelines in: data/guidelines/")
        print(f"   2. Run: python -m ingest.build_knowledge")
        print(f"   3. Start analyzing DPRs!")
    else:
        print(f"{Fore.RED}{Style.BRIGHT}⚠️  SOME CHECKS FAILED. Please fix the issues above.{Style.RESET_ALL}")
        sys.exit(1)
    
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
