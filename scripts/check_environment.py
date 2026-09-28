from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


def tesseract_path() -> str | None:
    candidates = [
        os.getenv("TESSERACT_CMD"),
        shutil.which("tesseract"),
        str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Tesseract-OCR" / "tesseract.exe"),
        str(Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Tesseract-OCR" / "tesseract.exe"),
    ]
    return next((p for p in candidates if p and Path(p).exists()), None)


report = {
    "platform": {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
    },
    "packages": {
        "fastapi": module("fastapi"),
        "pillow": module("PIL"),
        "numpy": module("numpy"),
        "opencv_optional": module("cv2"),
        "pymupdf": module("fitz"),
        "pytesseract": module("pytesseract"),
        "rapidocr_onnxruntime": module("rapidocr_onnxruntime"),
        "geniex": module("geniex"),
    },
    "executables": {
        "tesseract": tesseract_path(),
        "geniex": shutil.which("geniex") or shutil.which("geniex.exe"),
    },
    "services": {"geniex_18181": port_open("127.0.0.1", 18181)},
    "env": {
        "VEIL_OCR_PROVIDER": os.getenv("VEIL_OCR_PROVIDER", "auto"),
        "VEIL_SEMANTIC_PROVIDER": os.getenv("VEIL_SEMANTIC_PROVIDER", "auto"),
        "VEIL_SEMANTIC_MODEL": os.getenv("VEIL_SEMANTIC_MODEL", "ai-hub-models/Qwen3-4B-Instruct-2507"),
        "TESSERACT_CMD": os.getenv("TESSERACT_CMD"),
    },
}

print(json.dumps(report, indent=2))

if sys.version_info < (3, 11):
    print("\nERROR: Python 3.11+ is required.", file=sys.stderr)
    raise SystemExit(2)
if report["packages"]["pytesseract"] and not report["executables"]["tesseract"] and not report["packages"]["rapidocr_onnxruntime"]:
    print("\nNOTE: No operational OCR engine detected. The app can start, but live/file text detection needs Tesseract or RapidOCR.")
if platform.system() == "Windows" and platform.machine().lower() in {"arm64", "aarch64"} and not report["packages"]["geniex"]:
    print("\nNOTE: Windows ARM64 detected but GenieX is not installed. Run scripts/setup_snapdragon.ps1 for the Qualcomm path.")
if platform.system() == "Windows" and platform.machine().lower() in {"arm64", "aarch64"} and report["packages"]["opencv_optional"]:
    print("\nNOTE: OpenCV is optional. Confirm the installed build is genuinely compatible with the ARM64 Python environment before relying on face/file-QR masking.")
