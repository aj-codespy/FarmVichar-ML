# build_vector_db.py
import os
import faiss
import numpy as np
import google.generativeai as genai
from config import GEMINI_API_KEY, EMBEDDING_MODEL, VECTOR_DB_PATH, DOCS_PATH
from utils.rag_utils import embed_texts
import traceback

def run_build():
    """
    Reads text files, generates embeddings, and builds a FAISS vector index.
    This script should be run once before starting the app.
    """
    print("--- 🚀 Starting Vector Database Build Process ---")
    try:
        genai.configure(api_key=GEMINI_API_KEY)

        doc_dir = 'data/knowledge_docs'
        vector_db_dir = 'vector_db'

        # 1. Check for source documents
        print(f"[BUILD] Checking for source directory: '{doc_dir}'...")
        if not os.path.exists(doc_dir) or not os.listdir(doc_dir):
            print(f"❌ ERROR: The directory '{doc_dir}' is empty or does not exist.")
            print("Please create it and add your .txt knowledge files before running again.")
            return
        os.makedirs(vector_db_dir, exist_ok=True)
        print("[BUILD] Source directory found.")

        # 2. Load documents
        print("[BUILD] Loading documents from text files...")
        docs = []
        for filename in os.listdir(doc_dir):
            if filename.endswith('.txt'):
                with open(os.path.join(doc_dir, filename), 'r', encoding='utf-8') as f:
                    docs.append(f.read())
        print(f"[BUILD] Successfully loaded {len(docs)} documents.")

        if not docs:
            print("❌ ERROR: No .txt files were found in the knowledge_docs directory.")
            return

        # 3. Generate embeddings
        print(f"[BUILD] Generating embeddings using '{EMBEDDING_MODEL}'...")
        embeddings = embed_texts(docs)
        print(f"[BUILD] Embeddings generated with shape: {embeddings.shape}")

        # 4. Build and save FAISS index
        print("[BUILD] Building FAISS index...")
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        faiss.write_index(index, VECTOR_DB_PATH)
        print(f"[BUILD] FAISS index saved to '{VECTOR_DB_PATH}'")

        # 5. Save raw documents
        with open(DOCS_PATH, 'w', encoding='utf-8') as f:
            f.write('\n---\n'.join(docs))
        print(f"[BUILD] Raw documents saved to '{DOCS_PATH}'")

        print("--- ✅ Vector Database Build Process Completed Successfully! ---")

    except Exception as e:
        print(f"--- ❌ FATAL ERROR during Vector DB build: {e} ---")
        traceback.print_exc()

if __name__ == "__main__":
    run_build()