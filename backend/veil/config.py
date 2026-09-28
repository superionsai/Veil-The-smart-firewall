from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Veil"
    host: str = os.getenv("VEIL_HOST", "127.0.0.1")
    port: int = int(os.getenv("VEIL_PORT", "8080"))
    debug: bool = _env_bool("VEIL_DEBUG", False)

    data_dir: Path = Path(os.getenv("VEIL_DATA_DIR", ROOT / "data"))
    output_dir: Path = Path(os.getenv("VEIL_OUTPUT_DIR", ROOT / "outputs"))
    frontend_dir: Path = Path(os.getenv("VEIL_FRONTEND_DIR", ROOT / "frontend"))

    ocr_provider: str = os.getenv("VEIL_OCR_PROVIDER", "auto").lower()
    semantic_provider: str = os.getenv("VEIL_SEMANTIC_PROVIDER", "auto").lower()
    semantic_model: str = os.getenv(
        "VEIL_SEMANTIC_MODEL", "ai-hub-models/Qwen3-4B-Instruct-2507"
    )
    geniex_base_url: str = os.getenv("VEIL_GENIEX_BASE_URL", "http://127.0.0.1:18181/v1")
    geniex_device_map: str = os.getenv("VEIL_GENIEX_DEVICE_MAP", "qairt")

    live_jpeg_quality: int = int(os.getenv("VEIL_JPEG_QUALITY", "80"))
    live_process_interval_ms: int = int(os.getenv("VEIL_PROCESS_INTERVAL_MS", "450"))
    change_threshold: float = float(os.getenv("VEIL_CHANGE_THRESHOLD", "8.0"))
    changed_tile_fraction: float = float(os.getenv("VEIL_CHANGED_TILE_FRACTION", "0.025"))
    tile_size: int = int(os.getenv("VEIL_TILE_SIZE", "128"))
    change_padding: int = int(os.getenv("VEIL_CHANGE_PADDING", "24"))
    max_regions_per_frame: int = int(os.getenv("VEIL_MAX_REGIONS", "80"))
    semantic_batch_size: int = int(os.getenv("VEIL_SEMANTIC_BATCH_SIZE", "10"))
    semantic_min_chars: int = int(os.getenv("VEIL_SEMANTIC_MIN_CHARS", "8"))
    region_ttl_seconds: float = float(os.getenv("VEIL_REGION_TTL", "1.2"))
    audit_enabled: bool = _env_bool("VEIL_AUDIT_ENABLED", True)
    retain_raw_text: bool = _env_bool("VEIL_RETAIN_RAW_TEXT", False)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "veil.db"

    @property
    def platform_summary(self) -> dict[str, str]:
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        }

    @property
    def likely_snapdragon_windows(self) -> bool:
        return platform.system() == "Windows" and platform.machine().lower() in {
            "arm64",
            "aarch64",
        }


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
