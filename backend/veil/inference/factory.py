from __future__ import annotations

from ..config import Settings
from .base import SemanticProvider
from .geniex_direct import GenieXDirectProvider
from .geniex_server import GenieXServerProvider
from .heuristic import HeuristicProvider


def make_semantic_provider(settings: Settings) -> SemanticProvider:
    name = settings.semantic_provider
    if name == "heuristic":
        return HeuristicProvider()
    if name == "geniex_server":
        p = GenieXServerProvider(settings.geniex_base_url, settings.semantic_model)
        if not p.available():
            raise RuntimeError(f"GenieX server is not reachable at {settings.geniex_base_url}")
        return p
    if name == "geniex_direct":
        p = GenieXDirectProvider(settings.semantic_model, settings.geniex_device_map)
        if not p.available():
            raise RuntimeError("Python package 'geniex' is not installed/available")
        return p
    if name != "auto":
        raise ValueError(f"Unknown semantic provider: {name}")

    server = GenieXServerProvider(settings.geniex_base_url, settings.semantic_model)
    if server.available():
        return server
    if settings.likely_snapdragon_windows:
        direct = GenieXDirectProvider(settings.semantic_model, settings.geniex_device_map)
        if direct.available():
            return direct
    return HeuristicProvider()
