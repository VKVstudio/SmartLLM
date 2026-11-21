"""SmartLLM Studio v0.0.4-beta — Cross-Platform Local Multimodal Web & Design Workbench."""

from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parents[1] / "VERSION"
__version__ = _VERSION_FILE.read_text(encoding="utf-8").strip() if _VERSION_FILE.exists() else "0.0.4-beta"
__license__ = "FSL-1.1-ALv2"
