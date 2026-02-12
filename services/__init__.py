# Services : logique métier réutilisable (Streamlit + API)

from .jsonld_service import (
    extract_dom_structure,
    extract_semantic_features,
    cluster_pages,
    get_cluster_url_pattern,
    name_cluster_with_mistral,
    generate_optimized_jsonld,
    build_jsonld_graph_html,
    FLEXIBLE_TAGS,
    STRUCTURE_TAGS,
)

__all__ = [
    "extract_dom_structure",
    "extract_semantic_features",
    "cluster_pages",
    "get_cluster_url_pattern",
    "name_cluster_with_mistral",
    "generate_optimized_jsonld",
    "build_jsonld_graph_html",
    "FLEXIBLE_TAGS",
    "STRUCTURE_TAGS",
]
