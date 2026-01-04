"""Query rules and routing for multi-law retrieval."""
from .law_router import route_query, calculate_k_per_law

__all__ = ["route_query", "calculate_k_per_law"]

