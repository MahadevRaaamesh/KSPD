import os
import json
from typing import Optional
from config import settings
from models.schemas import SimilaritySearchResponse, SimilarFIRResult, FIR
from adapters.database import execute_query

class SimilarityService:
    def __init__(self):
        self.index = None
        self.id_map = None
        self.model = None

    async def initialize(self):
        try:
            import faiss
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print("Warning: faiss or sentence-transformers not installed. Similarity search disabled.")
            return

        if not os.path.exists(settings.FAISS_INDEX_PATH):
            print(f"Warning: FAISS index not found at {settings.FAISS_INDEX_PATH}. "
                  "Semantic search disabled — run scripts/build_embeddings.py to enable it.")
            return

        print("Loading FAISS index...")
        try:
            self.index = faiss.read_index(settings.FAISS_INDEX_PATH)
            id_map_path = settings.FAISS_INDEX_PATH.replace(".faiss", "_id_map.json")
            with open(id_map_path, "r") as f:
                self.id_map = {int(k): int(v) for k, v in json.load(f).items()}
        except (OSError, ValueError, json.JSONDecodeError) as e:
            print(f"Warning: could not load FAISS index/id map ({e}). "
                  "Semantic search disabled — rebuild with scripts/build_embeddings.py.")
            self.index = None
            self.id_map = None
            return

        print(f"Loading Embedding Model {settings.EMBEDDING_MODEL_NAME}...")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        print("Similarity Service Initialized.")

    async def get_fir_by_id(self, fir_id: int) -> Optional[FIR]:
        query = "SELECT * FROM FIRs WHERE ROWID = :fir_id"
        res = await execute_query(query, {"fir_id": fir_id})
        if not res:
            return None
        return FIR(**res[0])

    async def search_similar(
        self,
        text: str,
        top_k: int = 10,
        district: Optional[str] = None,
        crime_category: Optional[str] = None
    ) -> SimilaritySearchResponse:
        
        if not self.index or not self.model:
            return SimilaritySearchResponse(query_text=text, results=[], total_firs_indexed=0)
            
        import faiss
        
        query_vector = self.model.encode([text])
        faiss.normalize_L2(query_vector)
        
        fetch_k = top_k * 5 if (district or crime_category) else top_k
        distances, indices = self.index.search(query_vector, fetch_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1: continue
                
            fir_id = self.id_map.get(idx)
            if not fir_id: continue
                
            fir = await self.get_fir_by_id(fir_id)
            if not fir: continue
                
            if district and fir.district != district:
                continue
            if crime_category and fir.crime_major_head != crime_category:
                continue
                
            results.append(SimilarFIRResult(fir=fir, similarity_score=float(dist)))
            if len(results) >= top_k:
                break
                
        return SimilaritySearchResponse(
            query_text=text,
            results=results,
            total_firs_indexed=self.index.ntotal
        )

    async def search_by_fir_id(self, fir_id: int, top_k: int = 10) -> SimilaritySearchResponse:
        fir = await self.get_fir_by_id(fir_id)
        if not fir or not fir.brief_facts:
            return SimilaritySearchResponse(query_text="", results=[], total_firs_indexed=0)
            
        res = await self.search_similar(fir.brief_facts, top_k=top_k + 1)
        filtered_results = [r for r in res.results if r.fir.ROWID != fir_id][:top_k]
        res.results = filtered_results
        return res

similarity_service = SimilarityService()
