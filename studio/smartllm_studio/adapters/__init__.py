"""Studio RAG adapter: bundled design canon data is the source of truth.

The optional monorepo harvest selector is still importable for CLI tooling, but
Studio deliberately uses the bundled `StudioRAGSelector` so the 20 classical
canon cards, page taxonomy, and logo prompt rules ship together.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..rag import StudioRAGSelector


def get_rag_selector(repo_root: Path | None = None) -> Any:
    """Return the bundled Studio RAG selector (standalone-first, deterministic)."""
    _ = repo_root
    return StudioRAGSelector()


__all__ = ["get_rag_selector"]
