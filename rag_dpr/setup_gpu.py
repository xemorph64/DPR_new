"""
GPU Setup and Knowledge Base Builder
Installs CUDA PyTorch and rebuilds the vector database.
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and print status."""
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"{'='*70}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0

def main():
    venv_python = r"C:/Users/Ojas Bhalerao/Documents/RAG/rag_dpr/.venv/Scripts/python.exe"
    venv_pip = r"C:/Users/Ojas Bhalerao/Documents/RAG/rag_dpr/.venv/Scripts/pip.exe"
    
    print("GPU Setup & Knowledge Base Builder")
    print("="*70)
    
    # Step 1: Uninstall CPU PyTorch
    if not run_command(
        f'"{venv_pip}" uninstall torch torchvision torchaudio -y',
        "Step 1/3: Uninstalling CPU PyTorch"
    ):
        print("❌ Failed to uninstall PyTorch")
        return
    
    # Step 2: Install CUDA PyTorch
    if not run_command(
        f'"{venv_pip}" install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121',
        "Step 2/3: Installing CUDA 12.1 PyTorch"
    ):
        print("❌ Failed to install CUDA PyTorch")
        return
    
    # Step 3: Verify GPU
    print(f"\n{'='*70}")
    print("Step 3/3: Verifying GPU Detection")
    print("="*70)
    verify_result = subprocess.run(
        [venv_python, "-c", "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"],
        capture_output=True,
        text=True
    )
    print(verify_result.stdout)
    
    if "CUDA: True" in verify_result.stdout:
        print("GPU Successfully Detected!")
        
        # Step 4: Rebuild knowledge base
        print(f"\n{'='*70}")
        print("Building Knowledge Base with GPU")
        print("="*70)
        os.chdir(r"C:\Users\Ojas Bhalerao\Documents\RAG\rag_dpr")
        subprocess.run([venv_python, "-m", "ingest.build_knowledge"])
    else:
        print("GPU not detected. Knowledge base will use CPU.")
        print("\nTo use GPU, ensure:")
        print("1. NVIDIA drivers are installed")
        print("2. CUDA Toolkit is installed")
        print("3. Your GPU supports CUDA")

if __name__ == "__main__":
    main()
