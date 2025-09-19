# utils/rag_utils.py
import faiss
import os
import numpy as np
import google.generativeai as genai
from krishisakhi_api import config

# --- Initialize the Gemini Client Once ---
# This is more efficient than configuring it in every function call.
try:
    genai.configure(api_key=config.GEMINI_API_KEY)
except Exception as e:
    print(f"❌ ERROR: Failed to configure Gemini in rag_utils.py: {e}")


def load_faiss_index(index_path: str, docs_path: str):
    """
    Loads the FAISS index and the corresponding documents from disk.
    """
    print("[RAG] Attempting to load FAISS index and documents...")
    try:
        # Check if the required files exist before trying to load them
        if not os.path.exists(index_path) or not os.path.exists(docs_path):
            print(f"❌ ERROR [RAG]: Index file ('{index_path}') or docs file ('{docs_path}') not found.")
            return None, None

        index = faiss.read_index(index_path)
        with open(docs_path, 'r', encoding='utf-8') as f:
            docs = f.read().split('\n---\n')
        
        print(f"✅ [RAG] FAISS index with {index.ntotal} vectors and {len(docs)} documents loaded successfully.")
        return index, docs
        
    except Exception as e:
        print(f"❌ ERROR [RAG]: An unexpected error occurred while loading resources: {e}")
        return None, None

def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Generates embeddings for a list of texts in a single, efficient batch operation.
    """
    print(f"[RAG] Attempting to embed {len(texts)} text snippet(s)...")
    try:
        # Make a single API call for all texts for better performance
        result = genai.embed_content(model=config.EMBEDDING_MODEL, content=texts)
        print("[RAG] Embedding successful.")
        return np.array(result['embedding'], dtype=np.float32)
    except Exception as e:
        print(f"❌ ERROR [RAG]: Failed to generate embeddings. Reason: {e}")
        raise

def rag_retrieve(query: str, index: faiss.Index, docs: list[str], k: int = 3) -> str:
    """
    Retrieves the top-k most relevant document snippets from the vector DB.
    """
    print(f"[RAG] Retrieving context for query: '{query[:50]}...'")
    try:
        query_embedding = embed_texts([query])
        # Search the FAISS index
        distances, indices = index.search(query_embedding, k)
        
        # Retrieve the actual document chunks based on the search results
        relevant_docs = [docs[i] for i in indices[0] if i < len(docs)]
        context = "\n---\n".join(relevant_docs)
        
        print(f"[RAG] Retrieved {len(relevant_docs)} context snippets.")
        return context
    except Exception as e:
        print(f"❌ ERROR [RAG]: Failed during context retrieval. Reason: {e}")
        return "Error: Could not retrieve relevant context."