import asyncio
import os
import sys
import json
import numpy as np

# Add parent directory to path to import adapters and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.database import execute_query
from config import settings

try:
    import faiss
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Error: faiss and sentence-transformers are required for this script.")
    print("Install with: pip install faiss-cpu sentence-transformers")
    sys.exit(1)

async def build_index():
    print(f"Loading embedding model '{settings.EMBEDDING_MODEL_NAME}'...")
    model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    
    print("Fetching FIRs from database...")
    query = "SELECT CaseMasterID, BriefFacts FROM CaseMaster WHERE BriefFacts IS NOT NULL"
    firs = await execute_query(query)
    
    if not firs:
        print("No FIRs found with BriefFacts.")
        return
        
    print(f"Found {len(firs)} FIRs. Generating embeddings in batches...")
    
    texts = [f["BriefFacts"] for f in firs]
    fir_ids = [f["CaseMasterID"] for f in firs]
    
    # Generate embeddings
    embeddings = model.encode(texts, batch_size=256, show_progress_bar=True)
    
    # Normalize vectors for inner product (cosine similarity)
    faiss.normalize_L2(embeddings)
    
    dimension = embeddings.shape[1]
    print(f"Building FAISS IndexFlatIP (dim={dimension})...")
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    
    # Save index
    faiss_path = settings.FAISS_INDEX_PATH
    os.makedirs(os.path.dirname(faiss_path), exist_ok=True)
    faiss.write_index(index, faiss_path)
    
    # Save ID map
    id_map = {str(i): fir_id for i, fir_id in enumerate(fir_ids)}
    id_map_path = faiss_path.replace(".faiss", "_id_map.json")
    with open(id_map_path, "w") as f:
        json.dump(id_map, f)
        
    print(f"Success! Indexed {index.ntotal} FIRs.")
    print(f"Saved FAISS index to {faiss_path}")
    print(f"Saved ID map to {id_map_path}")

if __name__ == "__main__":
    asyncio.run(build_index())
