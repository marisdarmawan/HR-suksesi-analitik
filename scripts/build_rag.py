import sys
from pathlib import Path

# Add project root to python path so we can import utils
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from utils.rag_helper import build_vector_store

if __name__ == "__main__":
    print("Memulai proses indexing PDF...")
    try:
        build_vector_store()
        print("Proses indexing selesai!")
    except Exception as e:
        print(f"Terjadi kesalahan: {str(e)}")
