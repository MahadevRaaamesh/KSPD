import time
from typing import Any, Optional
from config import settings

class CacheManager:
    def __init__(self):
        self._local_cache = {}
        
    async def get(self, key: str) -> Optional[Any]:
        if settings.ENVIRONMENT == "local":
            if key in self._local_cache:
                entry = self._local_cache[key]
                if time.time() < entry["expires_at"]:
                    return entry["value"]
                else:
                    del self._local_cache[key]
            return None
            
        # Catalyst Cache logic would go here
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 300):
        if settings.ENVIRONMENT == "local":
            self._local_cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl_seconds
            }
            return
            
        # Catalyst Cache logic would go here
        
cache = CacheManager()
