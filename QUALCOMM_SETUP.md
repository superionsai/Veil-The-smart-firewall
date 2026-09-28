# Snapdragon / Qualcomm Setup

This document describes the intended competition-machine path.

## Target

- Windows 11 on ARM64
- Snapdragon X / X Plus / X Elite / X2-class PC supported by the chosen Qualcomm AI Hub model
- Python 3.11+ ARM64

## One-command project setup

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_snapdragon.ps1
```

To skip the model download during setup:

```powershell
.\scripts\setup_snapdragon.ps1 -SkipModelPull
```

## Direct GenieX mode (recommended)

```powershell
.\scripts\run_snapdragon.ps1
```

The script sets:

```text
VEIL_SEMANTIC_PROVIDER=geniex_direct
VEIL_SEMANTIC_MODEL=ai-hub-models/Qwen3-4B-Instruct-2507
VEIL_GENIEX_DEVICE_MAP=qairt
```

The model loads lazily on the first semantic request rather than at web-server startup.

## GenieX local server mode

Terminal A:

```powershell
.\.venv\Scripts\Activate.ps1
geniex pull ai-hub-models/Qwen3-4B-Instruct-2507
geniex serve
```

Terminal B:

```powershell
$env:VEIL_SEMANTIC_PROVIDER="geniex_server"
.\scripts\run.ps1
```

Veil defaults to `http://127.0.0.1:18181/v1`.

## Confirm runtime

Open Veil → **Diagnostics**.

Expected semantic runtime for direct mode:

```text
geniex_direct
```

Expected model:

```text
ai-hub-models/Qwen3-4B-Instruct-2507
```

Also run:

```powershell
.\scripts\check.ps1
```

## OCR on Snapdragon

Veil's **mandatory** Snapdragon path does not depend on OpenCV. Current public PyPI OpenCV distributions do not provide a Windows ARM64 wheel, so image decode/change detection/redaction use Pillow + NumPy instead. Do not install `requirements-optional.txt` blindly into the native ARM64 GenieX environment.

Veil's OCR is intentionally pluggable because OCR packaging can vary independently of GenieX.

Try:

1. local Tesseract + `pytesseract` (recommended practical fallback), or
2. RapidOCR if its ONNX Runtime dependency is compatible with the machine.

`TesseractOCR` checks `TESSERACT_CMD`, PATH, and common Windows installation locations. A separately installed x64 Tesseract process can still be invoked from the native ARM64 Python app on Windows-on-ARM; verify it on your competition laptop.

Set explicitly:

```powershell
$env:VEIL_OCR_PROVIDER="tesseract"
```

or:

```powershell
$env:VEIL_OCR_PROVIDER="rapidocr"
```

Then inspect `/api/health`.

Do not claim NPU-accelerated OCR in the presentation unless you actually deploy and measure it. Live QR masking can use Chromium's local `BarcodeDetector` without Python OpenCV; file QR/face masking requires an optional compatible visual backend. The scored Qualcomm path in this repository is the local semantic model through GenieX/QAIRT.

## Why Qwen3-4B-Instruct-2507

The challenge implementation needs:

- short structured classification,
- policy compilation,
- predictable JSON,
- enough context for batched OCR blocks,
- an official Qualcomm AI Hub / QAIRT path on Snapdragon compute devices.

The model can be changed using `VEIL_SEMANTIC_MODEL` without touching the app.

## Useful GenieX commands

```powershell
geniex list
geniex model list
geniex pull ai-hub-models/Qwen3-4B-Instruct-2507
geniex infer ai-hub-models/Qwen3-4B-Instruct-2507
geniex serve
```

Exact CLI behavior can change during developer-preview releases, so confirm against the installed GenieX version before the final presentation.

## References

- https://aihub.qualcomm.com/geniex
- https://github.com/qualcomm/GenieX
- https://github.com/qualcomm/GenieX/blob/main/docs/en/run/python/quickstart.mdx
- https://aihub.qualcomm.com/compute/models/qwen3_4b_instruct_2507
