import asyncio
import uuid
from typing import Optional, List

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class VectorMemory:
    """Semantic memory using ChromaDB for vector storage."""
    
    def __init__(
        self,
        collection_name: str = "chronos_memory",
        persist_directory: str = "./chroma_data"
    ) -> None:
        """
        Initialize vector memory with ChromaDB.
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist ChromaDB data
        """
        # Initialize persistent client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(name=collection_name)
        
        # Load embedding model
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def remember(self, user_id: int, text: str, metadata: Optional[dict] = None) -> str:
        """
        Store a text fragment in vector memory (async wrapper).
        
        Args:
            user_id: Telegram user ID
            text: Text to remember
            metadata: Additional metadata to store
            
        Returns:
            Memory ID (UUID)
        """
        # Run blocking embedding + ChromaDB add in thread pool
        return await asyncio.to_thread(self._remember_sync, user_id, text, metadata)
    
    def _remember_sync(self, user_id: int, text: str, metadata: Optional[dict] = None) -> str:
        """Synchronous implementation of remember."""
        # Generate embedding
        embedding = self.embedder.encode(text, convert_to_numpy=True).tolist()
        
        # Generate unique ID
        memory_id = f"{user_id}_{uuid.uuid4().hex}"
        
        # Prepare metadata
        meta = {"user_id": user_id, "text": text}
        if metadata:
            meta.update(metadata)
        
        # Add to collection
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            metadatas=[meta]
        )
        
        return memory_id
     
    async def recall(self, user_id: int, query: str, n_results: int = 5) -> List[str]:
        """
        Search for relevant memories by semantic similarity (async wrapper).
        
        Args:
            user_id: Telegram user ID
            query: Query text to search for
            n_results: Number of results to return
            
        Returns:
            List of memory texts sorted by relevance
        """
        # Run blocking embedding + ChromaDB query in thread pool
        return await asyncio.to_thread(self._recall_sync, user_id, query, n_results)
    
    def _recall_sync(self, user_id: int, query: str, n_results: int = 5) -> List[str]:
        """Synchronous implementation of recall."""
        # Generate query embedding
        query_embedding = self.embedder.encode(query, convert_to_numpy=True).tolist()
        
        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"user_id": user_id}
        )
        
        # Extract texts from metadatas
        texts = []
        if results and results.get("metadatas"):
            for meta_list in results["metadatas"]:
                for meta in meta_list:
                    texts.append(meta.get("text", ""))
        
        return texts
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory by ID (async wrapper).
        
        Args:
            memory_id: Memory ID to delete
            
        Returns:
            True if deleted, False otherwise
        """
        return await asyncio.to_thread(self._delete_memory_sync, memory_id)
    
    def _delete_memory_sync(self, memory_id: str) -> bool:
        """Synchronous implementation of delete_memory."""
        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception:
            return False
    
    async def clear_user_memories(self, user_id: int) -> int:
        """
        Delete all memories for a specific user (async wrapper).
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Number of memories deleted
        """
        return await asyncio.to_thread(self._clear_user_memories_sync, user_id)
    
    def _clear_user_memories_sync(self, user_id: int) -> int:
        """Synchronous implementation of clear_user_memories."""
        # Get all memories for user
        results = self.collection.get(where={"user_id": user_id})
        
        if results and results.get("ids"):
            ids = results["ids"]
            self.collection.delete(ids=ids)
            return len(ids)
        
        return 0


# Global instance (singleton)
_vector_memory: Optional[VectorMemory] = None


def get_vector_memory() -> VectorMemory:
    """Get or create global VectorMemory instance."""
    global _vector_memory
    if _vector_memory is None:
        _vector_memory = VectorMemory()
    return _vector_memory
