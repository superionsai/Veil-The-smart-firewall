# Snapdragon AI Lab Challenge — Final Checklist

## Before touching the submission form

- [ ] Confirm you satisfy the challenge eligibility requirements, including the required Snapdragon-powered laptop ownership.
- [ ] Re-read the current Official Rules, not only the summary page.
- [ ] Ensure this is your only submission; the challenge description says only the first eligible submission is considered.
- [ ] Do not put real credentials, private records, employer secrets or confidential material in screenshots/video/repository.
- [ ] Confirm every external model/library is allowed under its license/terms.
- [ ] Keep the original code/IP license decision intentional; this repository defaults to all rights reserved.

## Target-machine verification

Run:

```powershell
.\scripts\check.ps1
```

Confirm:

- [ ] Windows reports ARM64/AArch64.
- [ ] `geniex` is installed.
- [ ] `ai-hub-models/Qwen3-4B-Instruct-2507` is pulled/cached.
- [ ] Veil Diagnostics says `geniex_direct` or `geniex_server`.
- [ ] OCR backend is not `none`.
- [ ] Live Shield works with network disabled after all assets/models are cached.
- [ ] Custom policy compilation works locally.
- [ ] Synthetic PDF/image sanitization works.
- [ ] QR masking works under External/Public/Strict.
- [ ] `pytest` passes.

## Measurements to capture on the Snapdragon laptop

Do not use placeholder numbers. Record the machine/model/runtime with each result.

| Metric | Actual result |
|---|---|
| CPU / Snapdragon SKU | |
| RAM | |
| Windows version | |
| GenieX version | |
| Semantic model / precision | |
| OCR backend | |
| Text benchmark precision | |
| Text benchmark recall | |
| Image benchmark precision | |
| Image benchmark recall | |
| Leak rate | |
| Overmask rate | |
| Median live frame latency | |
| P95 live frame latency | |
| Event-driven skip rate | |
| Semantic model calls/minute | |
| Prefill/decode information from GenieX, if measured | |

Commands:

```powershell
$env:VEIL_SEMANTIC_PROVIDER="geniex_direct"
python benchmarks\run_benchmark.py --mode text --configured-provider
python benchmarks\run_benchmark.py --mode image --configured-provider --limit 60
```

## Screenshots for presentation

Capture these at high resolution:

- [ ] Live Shield before/after with fake credential.
- [ ] Semantic masking of `Project Orion acquisition estimate...`.
- [ ] Privacy Inspector explaining deterministic vs semantic source.
- [ ] Policy Studio input and compiled JSON.
- [ ] File Sanitizer protected PDF/image.
- [ ] Diagnostics showing GenieX model, platform and measured runtime.
- [ ] Benchmark table/plot made from actual target-machine results.

## Video flow

Use `DEMO_SCRIPT.md` and keep the demo around 3–4 minutes unless the challenge form states otherwise.

- [ ] Problem in <20 seconds.
- [ ] Prove local runtime early.
- [ ] Deterministic secret demo.
- [ ] Semantic confidential-text demo.
- [ ] Natural-language custom policy.
- [ ] PDF/image export.
- [ ] Technical cascade + event-driven metrics.
- [ ] Snapdragon relevance close.

## Claims not to make unless actually measured/implemented

- “100% leak prevention.”
- “Enterprise-grade DLP.”
- “NPU-accelerated OCR” unless you really deploy OCR on QNN/QAIRT.
- “Zero latency.”
- “Works inside every screen-sharing app automatically.”
- “No false positives/negatives.”
- Any benchmark number from the development/fallback environment.

## Submission text

Start from `SUBMISSION.md`, then replace generic descriptions with:

- exact HP/Snapdragon device,
- actual model/runtime configuration,
- actual benchmarks,
- link/attachment requested by the challenge form,
- short demo video,
- architecture screenshot.

## Final smoke test, immediately before submission

```powershell
.\scripts\check.ps1
.\scripts\run_snapdragon.ps1
```

Then manually test:

1. fake API key,
2. fake confidential sentence,
3. custom `Project Orion` rule,
4. synthetic PDF,
5. QR code,
6. diagnostics.

Only submit after the exact artifact/video you are uploading has been opened and watched once from start to finish.
