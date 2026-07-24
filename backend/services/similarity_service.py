import os
import json
import numpy as np
from typing import Optional, List
from config import settings
from models.schemas import SimilaritySearchResponse, SimilarFIRResult, FIR
from adapters.database import execute_query

class SimilarityService:
    """Singleton — initialized once at app startup."""
    
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
            print(f"Warning: FAISS index not found at {settings.FAISS_INDEX_PATH}. Run build_embeddings.py first.")
            return
            
        print("Loading FAISS index...")
        self.index = faiss.read_index(settings.FAISS_INDEX_PATH)
        
        id_map_path = settings.FAISS_INDEX_PATH.replace(".faiss", "_id_map.json")
        with open(id_map_path, "r") as f:
            # Convert string keys back to int indices, keep values as int
            self.id_map = {int(k): int(v) for k, v in json.load(f).items()}
            
        print(f"Loading Embedding Model {settings.EMBEDDING_MODEL_NAME}...")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        print("Similarity Service Initialized.")

    async def get_fir_by_id(self, fir_id: int) -> Optional[FIR]:
        query = """
            SELECT c.*, ch.CrimeGroupName, u.UnitName, d.DistrictName, s.CaseStatusName
            FROM CaseMaster c
            LEFT JOIN CrimeHead ch ON c.CrimeMajorHeadID = ch.CrimeHeadID
            LEFT JOIN Unit u ON c.PoliceStationID = u.UnitID
            LEFT JOIN District d ON u.DistrictID = d.DistrictID
            LEFT JOIN CaseStatusMaster s ON c.CaseStatusID = s.CaseStatusID
            WHERE c.CaseMasterID = :fir_id
        """
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
        
        # 1. Encode query
        query_vector = self.model.encode([text])
        faiss.normalize_L2(query_vector)
        
        # 2. Search FAISS (fetch more because we might filter)
        fetch_k = top_k * 5 if (district or crime_category) else top_k
        distances, indices = self.index.search(query_vector, fetch_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
                
            fir_id = self.id_map.get(idx)
            if not fir_id:
                continue
                
            fir = await self.get_fir_by_id(fir_id)
            if not fir:
                continue
                
            # 3. Apply Filters
            if district and fir.DistrictName != district:
                continue
            if crime_category and fir.CrimeGroupName != crime_category:
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
        if not fir or not fir.BriefFacts:
            return SimilaritySearchResponse(query_text="", results=[], total_firs_indexed=0)
            
        # Search using the FIR's brief facts
        # Add 1 to top_k because the first result will be the FIR itself
        res = await self.search_similar(fir.BriefFacts, top_k=top_k + 1)
        
        # Filter out self
        filtered_results = [r for r in res.results if r.fir.CaseMasterID != fir_id][:top_k]
        res.results = filtered_results
        return res

similarity_service = SimilarityService()
