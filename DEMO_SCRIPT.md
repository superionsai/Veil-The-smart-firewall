# 3–4 Minute Challenge Demo Script

## 0:00–0:20 — problem

Show a normal developer/work screen with a deliberately fake token and a confidential sentence.

Narration:

> Screen sharing is a surprisingly easy data-loss channel. Traditional pattern matching can catch a token, but it cannot understand that “Project Orion acquisition estimate” is confidential in this meeting. Sending the screen to a cloud AI to decide would expose the very data we are trying to protect.

## 0:20–0:40 — local proof

Open **Diagnostics** first.

Show:

- semantic provider = GenieX direct/server,
- model name,
- Windows ARM64 platform,
- local OCR backend,
- no cloud endpoint.

Optional: disable Wi-Fi before the recorded demo if your full stack has already been downloaded and verified offline.

## 0:40–1:25 — Live Shield deterministic + semantic

1. Select **External Meeting**.
2. Click **Protect a window** and select the prepared fake workspace.
3. Show `ghp_FAKE...` / `sk-FAKE...` being blocked by deterministic detection.
4. Show a plain sentence such as:

```text
Project Orion acquisition estimate: ₹350 crore. Do not share externally.
```

5. Highlight that the semantic classifier masks it even though it is not a token format.

Point at Privacy Inspector:

- category,
- confidence,
- source,
- reason.

## 1:25–1:55 — policy compiler

Open **Policy Studio**.

Compile:

```text
Hide credentials, salary information, personal phone numbers and anything about Project Orion. QR codes should also be hidden.
```

Show the resulting structured policy JSON, then return to Live Shield.

Change the fake source to include `Project Orion`. Show that the exact custom concept is protected.

## 1:55–2:25 — file sanitization

Upload the generated fake PDF from `benchmarks/sample_data/`.

Show:

- protected copy,
- detection count,
- PDF note explaining rasterization removes the original text layer.

Download and open it if time allows.

## 2:25–2:55 — technical differentiation

Open **Diagnostics**.

Explain:

> Veil does not run a 4B model on every frame. It detects changed screen tiles, OCRs only changed regions, catches deterministic secrets first, filters obvious UI text, batches ambiguous text, and caches semantic decisions. Static masks stay active even when the frame is skipped.

Show:

- skip rate,
- semantic call count,
- average latency.

## 2:55–3:20 — Snapdragon relevance

Narration:

> The core contradiction in privacy protection is that cloud inference requires sending sensitive content away before deciding whether it is sensitive. On Snapdragon, GenieX and QAIRT let the semantic classifier run locally on the NPU. That makes on-device compute part of the product requirement rather than a deployment afterthought.

## 3:20–3:35 — close

> Veil turns the AI PC into the privacy boundary: detect locally, reason locally, share safely.
