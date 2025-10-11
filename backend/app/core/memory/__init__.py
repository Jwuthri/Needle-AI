"""
Memory implementations for NeedleAi.

This module provides both Agno-based (preferred) and custom memory implementations
with automatic fallback logic.
"""

# Export memory interface
from .base import MemoryInterface

# Export Agno-based implementations (preferred)
try:
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False

# Export factory functions
from .factory import (
    MemoryFactory,
    MemoryProvider,
    create_custom_memory_only,
    create_memory_from_settings,
    get_memory_store,
)
from .in_memory import InMemoryStore

# Export custom implementations (fallback)
from .redis_memory import RedisMemory

# Note: Vector database implementations (Pinecone, Weaviate, Qdrant, ChromaDB)
# are now provided by Agno and are much more robust than our old custom implementations


# Export capability information
__all__ = [
    # Base interface
    "MemoryInterface",

    # Factory functions (main entry points)
    "MemoryFactory",
    "MemoryProvider",
    "create_memory_from_settings",
    "get_memory_store",

    # Custom implementations (always available)
    "RedisMemory",
    "InMemoryStore",

    # Agno implementations (if available) - preferred for vector databases
    *([
        "AgnoMemoryInterface",
        "AgnoPineconeMemory",
        "AgnoWeaviateMemory",
        "AgnoQdrantMemory",
        "AgnoChromaMemory",
        "AgnoChatMemory",
        "AgnoRedisMemory",
        "AgnoMemoryFactory",
        "create_agno_memory_only"
    ] if AGNO_AVAILABLE else []),

    # Advanced factory functions
    "create_custom_memory_only",
]

# Capability flags
CAPABILITIES = {
    "agno": AGNO_AVAILABLE,
    "pinecone": AGNO_AVAILABLE,  # Available through Agno
    "weaviate": AGNO_AVAILABLE,  # Available through Agno
    "qdrant": AGNO_AVAILABLE,    # Available through Agno
    "chromadb": AGNO_AVAILABLE,  # Available through Agno
    "redis": True,               # Always available (custom + Agno)
    "in_memory": True,           # Always available (custom fallback)
}
