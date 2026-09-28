# Security and Privacy Notes

Veil is a challenge prototype designed around local processing. It should not be represented as certified DLP/security software.

## Threats addressed

- accidental screen-share exposure of credentials/PII/confidential text,
- accidental sharing of sensitive image/PDF pixels,
- recoverable hidden text in visually redacted PDFs,
- cloud privacy contradiction where private content must be uploaded to decide whether it is private,
- persistent storage of OCR text in application logs.

## Safeguards implemented

- server binds to localhost by default,
- no cloud API required,
- raw OCR text is not persisted by default,
- audit text is hashed,
- PDF output is rasterized after redaction,
- raw live frame is held off-screen and the visible protected canvas updates only after detection returns,
- deterministic secret detectors run before semantic inference,
- structured bounded semantic output,
- explicit browser screen-capture permission,
- randomized output filenames.

## Known limitations

- OCR errors can cause false negatives.
- Semantic models can misclassify.
- Regex patterns are necessarily incomplete.
- Haar face detection is a convenience feature, not a robust production face detector.
- A compromised endpoint/browser/OS can access data outside Veil's trust boundary.
- If the user shares the original source window instead of the Veil output, Veil cannot protect that separate share stream.
- The browser implementation is not a virtual display driver or operating-system DLP layer.
- Text hashes can still be vulnerable to guessing attacks for very small/known vocabularies; they are used only as a low-retention demo audit mechanism.

## Safer demo practice

Use only fake credentials, fake identifiers and synthetic company/project names. Do not test the public demo with real passwords, OTPs, account details, API tokens, medical data or customer documents.
