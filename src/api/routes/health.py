"""Health and diagnostics route."""

from fastapi import APIRouter
from src.core.config import settings

router = APIRouter()


@router.get("/health", tags=["system"])
async def health_check():
    """Returns system status, active engine mode, DocJev availability, and 4-layer pipeline details."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "author": settings.author,
        "engine_mode": settings.active_engine_mode,
        "has_llm_key": settings.has_llm_key,
        "has_typesafe_key": settings.has_typesafe_key,
        "can_use_docjev": settings.can_use_docjev,
        "supported_formats": settings.allowed_extensions,
        "adaptive_layers": {
            "layer_1_ingestion": "spatial_column_block_sorting",
            "layer_2_packet_splitter": "docjev_typesafe" if settings.can_use_docjev else "heuristic_boundary_splitter",
            "layer_3_normalizer": "fuzzy_typographic_80_aliases",
            "layer_4_extractor": "neuro_symbolic_hybrid_reconciliation" if settings.has_llm_key else "deterministic_heuristics"
        }
    }
