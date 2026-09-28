from __future__ import annotations

from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks" / "sample_data"
OUT.mkdir(parents=True, exist_ok=True)


def font(size: int, mono: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf" if mono else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/consola.ttf" if mono else "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Menlo.ttc" if mono else "/System/Library/Fonts/SFNS.ttf",
    ]
    for p in candidates:
        try:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def workspace_image() -> Image.Image:
    W, H = 1600, 980
    img = Image.new("RGB", (W, H), "#101318")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 70), fill="#171b22")
    d.text((30, 20), "VEIL DEMO — SYNTHETIC DATA ONLY", fill="#8cf5c8", font=font(26))
    d.rectangle((28, 95, 1020, 930), fill="#0c0f14", outline="#2f3542", width=2)
    d.text((52, 118), "deploy.env", fill="#d7dae0", font=font(20, True))
    lines = [
        ('SERVICE_NAME="orion-console"', "#c5cad4"),
        ('OPENAI_KEY="sk-THIS_IS_A_FAKE_DEMO_TOKEN_123456789"', "#f3b0b8"),
        ('GITHUB_TOKEN="ghp_FAKEDEMO1234567890123456789012"', "#f3b0b8"),
        ('DATABASE_URL="postgres://demo:fakepassword@localhost:5432/veil"', "#f3b0b8"),
        ('PUBLIC_ENDPOINT="https://example.invalid"', "#a9cfb9"),
        ('SUPPORT_EMAIL="demo.user@example.com"', "#e6cf8f"),
        ('MOBILE="9876543210"', "#e6cf8f"),
        ('# All values on this screen are fabricated for the competition demo.', "#6f7787"),
    ]
    y = 165
    for text, colour in lines:
        d.text((58, y), text, fill=colour, font=font(22, True)); y += 46

    d.rectangle((1050, 95, 1570, 520), fill="#131820", outline="#2f3542", width=2)
    d.text((1080, 120), "Private team chat", fill="#d7dae0", font=font(22))
    messages = [
        "Priya  14:32",
        "Project Orion acquisition estimate:",
        "₹350 crore. Do not share externally.",
        "",
        "Recruiting  14:36",
        "Candidate offer: ₹21 LPA approved.",
        "Please keep this private until Friday.",
    ]
    y = 170
    for line in messages:
        col = "#aeb6c5" if (":" not in line and "₹" not in line and "Project" not in line and "Please" not in line) else "#f1d4a4"
        d.text((1080, y), line, fill=col, font=font(19)); y += 42

    d.rectangle((1050, 550, 1570, 930), fill="#131820", outline="#2f3542", width=2)
    d.text((1080, 578), "Safe public notes", fill="#d7dae0", font=font(22))
    safe = ["Meeting moved to Friday.", "Build completed successfully.", "Documentation updated.", "localhost:8080 is running."]
    y = 630
    for line in safe:
        d.text((1080, y), line, fill="#a9cfb9", font=font(19)); y += 44

    # Synthetic QR demonstrates non-text visual masking. It encodes no real secret.
    try:
        import qrcode
        qr_img = qrcode.make("VEIL-DEMO-FAKE-SESSION=NOT-A-REAL-SECRET").convert("RGB").resize((150, 150), Image.Resampling.NEAREST)
        img.paste(qr_img, (1380, 745))
        d.text((1370, 710), "Synthetic access QR", fill="#e6cf8f", font=font(15))
    except Exception:
        d.rectangle((1380, 745, 1530, 895), fill="white", outline="#777")
        d.text((1390, 808), "QR demo\n(qrcode optional)", fill="black", font=font(13))
    return img


img = workspace_image()
png = OUT / "synthetic_workspace.png"
img.save(png, quality=95)

# Create a two-page PDF containing synthetic information only.
doc = fitz.open()
for title, body in [
    ("Synthetic Client Brief", ["Client: Project Orion", "Budget estimate: ₹350 crore", "Status: CONFIDENTIAL — external sharing prohibited", "Contact: demo.user@example.com"]),
    ("Synthetic Operations Notes", ["DATABASE_URL=postgres://demo:fakepassword@localhost:5432/veil", "Meeting moved to Friday.", "No real secrets are included in this document."]),
]:
    page = doc.new_page(width=595, height=842)
    page.insert_text((55, 80), title, fontsize=22)
    y = 130
    for line in body:
        # Built-in PDF fonts cannot encode every Unicode symbol; replace only in
        # the synthetic demo PDF, not in the application pipeline itself.
        page.insert_text((55, y), line.replace("₹", "INR ").replace("—", "-"), fontsize=13)
        y += 32
pdf = OUT / "synthetic_confidential.pdf"
doc.save(pdf)
doc.close()

text = OUT / "synthetic_paste.txt"
text.write_text(
    "OPENAI_KEY=sk-THIS_IS_A_FAKE_DEMO_TOKEN_123456789\n"
    "Project Orion acquisition estimate is confidential and must not be shared externally.\n"
    "Meeting moved to Friday.\n",
    encoding="utf-8",
)

print(f"Generated:\n- {png}\n- {pdf}\n- {text}")
