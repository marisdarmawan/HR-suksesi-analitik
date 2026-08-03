import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Path management
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data' / 'raw'
FAISS_INDEX_DIR = BASE_DIR / 'data' / 'faiss_index'

PDF_FILENAME = "2023.12.28 Peraturan Pelaksana PT PLN (Persero) Nomor 0050.E-DIR-2023 tentang Standar Prosedur Sistem Manajemen Talenta dan Pegawai PT PLN (Persero).PDF"
PDF_PATH = DATA_DIR / PDF_FILENAME

def get_embeddings():
    """Menggunakan model embedding lokal (HuggingFace) yang tidak butuh API Key"""
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def build_vector_store():
    """
    Membaca PDF Perdir, memotong teks, dan menyimpannya ke FAISS vector store lokal.
    Hanya perlu dijalankan sekali via script terpisah.
    """
    print(f"Membaca dokumen: {PDF_PATH}")
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"File PDF tidak ditemukan di {PDF_PATH}")

    # Load PDF
    loader = PyPDFLoader(str(PDF_PATH))
    docs = loader.load()
    
    print(f"Dokumen dimuat. Total {len(docs)} halaman.")
    
    # Text Splitting
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = text_splitter.split_documents(docs)
    print(f"Teks dipotong menjadi {len(chunks)} chunks.")
    
    # Embeddings
    print("Membuat embeddings menggunakan model lokal HuggingFace (all-MiniLM-L6-v2)...")
    embeddings = get_embeddings()
    
    # Create Vector Store
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    # Save locally
    os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
    vectorstore.save_local(str(FAISS_INDEX_DIR))
    print(f"Vector store berhasil disimpan di: {FAISS_INDEX_DIR}")

def query_peraturan(pertanyaan: str) -> str:
    """
    Fungsi untuk mencari jawaban dari FAISS vector store.
    Ini yang akan dipanggil oleh chatbot tool.
    """
    if not os.path.exists(FAISS_INDEX_DIR):
        return "Mohon maaf, database peraturan (FAISS Index) belum di-build. Silakan jalankan script build_rag.py terlebih dahulu."
        
    embeddings = get_embeddings()
    
    # Load index yang sudah ada
    vectorstore = FAISS.load_local(str(FAISS_INDEX_DIR), embeddings, allow_dangerous_deserialization=True)
    
    # Melakukan Similarity Search
    docs = vectorstore.similarity_search(pertanyaan, k=4)
    
    if not docs:
        return "Tidak ditemukan referensi yang relevan di dalam Perdir No. 0050.E-DIR-2023."
        
    # Ekstrak isi teks dari dokumen yang relevan
    context = "\n\n---\n\n".join([f"Kutipan Halaman {d.metadata.get('page', '?')}:\n{d.page_content}" for d in docs])
    
    return f"REFERENSI DARI PERDIR NO. 0050.E-DIR-2023:\n\n{context}"
