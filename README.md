# Veil

**On-device semantic privacy firewall for Snapdragon AI PCs.**

Veil protects users from accidental information leakage while screen-sharing, sharing screenshots/PDFs, or copying text. It combines deterministic secret/PII detection, OCR-grounded semantic classification, visual QR/face detection, natural-language privacy policies, event-driven screen analysis, temporal mask tracking, and an optional Qualcomm GenieX / QAIRT path for local NPU inference.

> Challenge target: **Snapdragon® AI Lab Build & Present Challenge — Qualcomm**  
> Product principle: **the content that needs protection should not have to leave the PC in order to be protected.**

## What is implemented

- **Live Shield** — select a source window/screen, process locally, and share Veil's protected preview instead of the raw source.
- **Fail-closed preview rendering** — Veil does not flash a raw frame and redact it later; the preview is updated only after the corresponding privacy decision arrives.
- **Event-driven OCR** — tile-based change detection only reprocesses changed screen regions.
- **Temporal mask tracking** — static sensitive regions remain masked without repeated OCR/LLM calls; changed regions must be revalidated.
- **Deterministic detectors** — API keys, GitHub tokens, JWTs, database URLs, credential assignments, PAN-like IDs, phone/email, IFSC/UPI, Aadhaar-format candidates, and Luhn-valid card numbers.
- **Semantic privacy layer** — confidential work, private communications, health/location context, and custom protected concepts.
- **Confidence-gated model escalation** — deterministic detections bypass the LLM; UI noise is filtered; ambiguous OCR blocks are batched and cached before semantic inference.
- **Natural-language Policy Studio** — e.g. “hide credentials, salary details and anything about Project Orion.”
- **File Sanitizer** — image and PDF export. PDFs are rasterized after masking to remove the original selectable text layer.
- **Quick Paste** — redact secrets and semantic-sensitive lines in text before copying.
- **QR masking + optional face blurring** — OpenCV-based visual privacy signals.
- **Privacy-preserving audit log** — category/action/source/confidence/text hash; raw OCR text is disabled by default.
- **Diagnostics dashboard** — average latency, change/skip rate, semantic calls, selected OCR/runtime, audit counts.
- **Cross-platform development fallback** — runs on ordinary Windows/macOS/Linux with heuristic semantic classification; Snapdragon acceleration is isolated behind a provider interface.

## Architecture

```text
                      LIVE SCREEN / IMAGE / PDF / TEXT
                                   │
                                   ▼
                      ┌────────────────────────┐
                      │ Input / frame manager  │
                      └───────────┬────────────┘
                                  │
                 live video only  ▼
                      ┌────────────────────────┐
                      │ Tile change detection  │
                      └───────────┬────────────┘
                                  │ changed regions only
                                  ▼
                      ┌────────────────────────┐
                      │ Local OCR              │
                      │ RapidOCR/Tesseract     │
                      └───────────┬────────────┘
                                  │ text + boxes
                   ┌──────────────┴──────────────┐
                   ▼                             ▼
       ┌──────────────────────┐      ┌──────────────────────┐
       │ Deterministic rules  │      │ Semantic escalation  │
       │ regex + Luhn + etc.  │      │ local LLM / GenieX   │
       └──────────┬───────────┘      └──────────┬───────────┘
                  │                             │
                  └──────────────┬──────────────┘
                                 ▼
                     ┌────────────────────────┐
                     │ Privacy policy engine  │
                     └───────────┬────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │ Temporal mask tracker  │
                     └───────────┬────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │ block / blur / warn    │
                     └───────────┬────────────┘
                                 ▼
                          PROTECTED OUTPUT
```

The local generative model is **not** asked to locate pixels. OCR produces the bounding boxes; the semantic model only classifies ambiguous text. This sharply reduces generative calls and keeps the output geometrically grounded.

## Recommended challenge configuration: Snapdragon Windows ARM64

Use **Python 3.11+ ARM64**. Qualcomm's current GenieX Python distribution supports Windows ARM64 and exposes `AutoModelForCausalLM.from_pretrained(...)`; QAIRT bundles can be selected with `device_map="qairt"`.

Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup_snapdragon.ps1
.\scripts\run_snapdragon.ps1
```

The setup script:

1. creates `.venv`,
2. installs Veil dependencies,
3. installs `geniex`,
4. optionally pulls `ai-hub-models/Qwen3-4B-Instruct-2507`,
5. runs the test suite and environment check.

Then open:

```text
http://127.0.0.1:8080
```

### Alternative: GenieX local server mode

This is useful if you want to demonstrate the OpenAI-compatible local endpoint separately:

```powershell
geniex pull ai-hub-models/Qwen3-4B-Instruct-2507
geniex serve
```

In another terminal:

```powershell
$env:VEIL_SEMANTIC_PROVIDER="geniex_server"
.\scripts\run.ps1
```

Veil will call `http://127.0.0.1:18181/v1/chat/completions` by default. This is still local-only.

## Ordinary laptop / development setup

### Windows

```powershell
.\scripts\setup.ps1
.\scripts\run.ps1
```

### Linux/macOS

```bash
chmod +x scripts/*.sh
./scripts/setup.sh
./scripts/run.sh
```

If no local generative runtime is found, Veil uses its deterministic + heuristic semantic fallback. This fallback exists so the UI, policies, tests, files, capture path and benchmark harness can be developed without the competition laptop.

## OCR choices

Set with `VEIL_OCR_PROVIDER`:

- `auto` — try RapidOCR if installed, then Tesseract, then a no-OCR fallback.
- `rapidocr` — use `rapidocr-onnxruntime` (optional dependency; platform compatibility varies).
- `tesseract` — use a locally installed Tesseract executable through `pytesseract`.
- `none` — useful only for API/UI development and deterministic unit tests.

Check the selected backend on the **Diagnostics** tab or:

```bash
curl http://127.0.0.1:8080/api/health
```

For the challenge machine, validate OCR early. OCR packaging differs more across Windows ARM environments than the rest of the app. The semantic/Qualcomm path is deliberately independent from OCR so an OCR backend can be swapped without modifying the privacy pipeline.

## Semantic provider choices

Set `VEIL_SEMANTIC_PROVIDER`:

| Provider | Use case |
|---|---|
| `auto` | GenieX server if reachable → direct GenieX on Windows ARM64 → heuristic fallback |
| `geniex_direct` | Direct Python GenieX API, recommended challenge path |
| `geniex_server` | Local OpenAI-compatible GenieX server |
| `heuristic` | No-model development fallback |

Defaults:

```text
VEIL_SEMANTIC_MODEL=ai-hub-models/Qwen3-4B-Instruct-2507
VEIL_GENIEX_DEVICE_MAP=qairt
```

## Privacy profiles

- **Public Presentation** — masks contact/identity/financial/work/private/health/location, QR codes and faces.
- **External Meeting** — masks credentials, personal data, confidential work/private messages, health/location and QR codes.
- **Internal Meeting** — hard-blocks credentials/identity/financial/health; lighter warnings/allowances for internal collaboration.
- **Strict Privacy** — mask everything Veil recognizes, plus faces and QR codes.
- **Custom Policy** — generated in Policy Studio and inspectable as JSON.

## Live Shield: correct demo workflow

1. Open Veil.
2. Choose **External Meeting**.
3. Click **Protect a window**.
4. Select VS Code, a browser, terminal, or another test source.
5. Keep Veil's **Protected output** visible.
6. In Teams/Meet/Zoom, share the **Veil tab/window**, not the source.
7. Demonstrate deterministic masking first, then semantic masking, then a custom protected concept.

A browser app cannot magically replace another program's screen-share feed without a capture/virtual-display driver. Veil intentionally avoids that fragile driver scope for the competition MVP and makes the protected output explicit and auditable.

## Demo data

Generate deliberately fake challenge assets:

```bash
python scripts/generate_demo_assets.py
```

This creates files under `benchmarks/sample_data/`, including a fake “developer workspace” screenshot and a PDF. Do not use real credentials or real personal data in the presentation.

## Tests

```bash
pytest
```

Key test coverage includes:

- Luhn and Verhoeff validators,
- deterministic token/PII detection,
- privacy profile actions,
- natural-language policy compilation fallback,
- Quick Paste sanitization,
- change detection,
- temporal-region persistence,
- API health/text endpoint smoke tests.

## Benchmarks

Run deterministic/semantic text benchmark:

```bash
python benchmarks/run_benchmark.py --mode text
```

Run the OCR + full image pipeline benchmark after generating assets and confirming OCR:

```bash
python scripts/generate_demo_assets.py
python benchmarks/run_benchmark.py --mode image
```

The benchmark emits JSON to `benchmarks/results/` and reports:

- precision,
- recall,
- F1,
- leak rate = FN / total sensitive examples,
- overmask rate = FP / total safe examples,
- mean/median processing latency,
- semantic provider calls.

For the submission, compare:

1. semantic-only classification,
2. deterministic + semantic cascade,
3. full Veil event-driven cascade.

Do **not** invent benchmark numbers. Record the actual measurements on the Snapdragon laptop and place them in your slides/submission.

## Security/privacy choices

- No cloud API is required.
- `VEIL_RETAIN_RAW_TEXT=0` by default.
- Audit records store a SHA-256 text hash rather than raw OCR text.
- Protected PDFs are rasterized to prevent recovery from the original text layer.
- Screen capture happens through the browser's permission-controlled `getDisplayMedia` flow.
- Veil binds to `127.0.0.1` by default.
- Generated outputs use randomized file names.
- Semantic model prompts ask for bounded JSON, not unrestricted agent actions.

See [`SECURITY.md`](SECURITY.md) for threat model and known limitations.

## Repository map

```text
veil/
├── backend/veil/
│   ├── core/           # frame processing, change detection, redaction, file/text sanitizers
│   ├── detection/      # deterministic validators + QR/face detection
│   ├── inference/      # heuristic, GenieX direct/server, semantic batching/cache
│   ├── metrics/        # runtime metrics + privacy-preserving SQLite audit
│   ├── ocr/            # OCR provider interface and implementations
│   ├── policy/         # presets, engine, natural-language compiler
│   ├── tracking/       # temporal mask persistence
│   └── main.py         # FastAPI + WebSocket API
├── frontend/           # zero-build HTML/CSS/JS UI
├── benchmarks/         # reproducible benchmark harness
├── scripts/            # setup/run/verify/demo helpers
├── tests/              # unit + smoke tests
├── ARCHITECTURE.md
├── DEMO_SCRIPT.md
├── QUALCOMM_SETUP.md
├── SECURITY.md
└── SUBMISSION.md
```

## Qualcomm references used by this implementation

- GenieX overview / Windows / Python / local server: <https://aihub.qualcomm.com/geniex>
- Qualcomm GenieX GitHub: <https://github.com/qualcomm/GenieX>
- Python quickstart: <https://github.com/qualcomm/GenieX/blob/main/docs/en/run/python/quickstart.mdx>
- Qwen3-4B-Instruct-2507 Qualcomm AI Hub entry: <https://aihub.qualcomm.com/compute/models/qwen3_4b_instruct_2507>
- ONNX Runtime QNN provider (possible future OCR acceleration path): <https://github.com/onnxruntime/onnxruntime-qnn>

## Scope boundaries

Veil is a competition prototype, not a certified enterprise DLP product. It can miss secrets, OCR can fail, semantic models can misclassify, and browser screen capture cannot intercept arbitrary OS/app sharing without deeper system integration. These limitations are explicitly surfaced rather than hidden.

## License

MIT for this repository's original code. Third-party packages/models remain under their own licenses and terms. Verify the challenge rules and each model/runtime license before final submission/distribution.
