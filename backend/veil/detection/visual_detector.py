from __future__ import annotations

import numpy as np
from PIL import Image

from ..models import Box, PrivacyCategory, PrivacyRegion


class VisualDetector:
    """Optional OpenCV-powered QR/face detector.

    OpenCV is deliberately *not* a hard dependency because official PyPI wheels
    are not consistently available for native Windows ARM64. The core Veil
    privacy pipeline works without this module. Live QR masking also has a
    browser BarcodeDetector path in the frontend when Chromium exposes it.
    """

    def __init__(self):
        self.cv2 = None
        self.qr = None
        self.face = None
        try:
            import cv2
            self.cv2 = cv2
            self.qr = cv2.QRCodeDetector()
            try:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                face = cv2.CascadeClassifier(cascade_path)
                if not face.empty():
                    self.face = face
            except Exception:
                self.face = None
        except Exception:
            pass

    @property
    def available(self) -> bool:
        return self.cv2 is not None

    def detect(self, image: Image.Image, mask_qr: bool, mask_faces: bool) -> list[PrivacyRegion]:
        if not self.available:
            return []
        rgb = np.asarray(image.convert("RGB"))
        bgr = rgb[:, :, ::-1].copy()
        regions: list[PrivacyRegion] = []
        if mask_qr:
            regions.extend(self._detect_qr(bgr))
        if mask_faces:
            regions.extend(self._detect_faces(bgr))
        return regions

    def _detect_qr(self, image_bgr: np.ndarray) -> list[PrivacyRegion]:
        out: list[PrivacyRegion] = []
        if self.qr is None:
            return out
        try:
            ok, _decoded_info, points, _ = self.qr.detectAndDecodeMulti(image_bgr)
            if ok and points is not None:
                for pts in points:
                    xs = pts[:, 0]
                    ys = pts[:, 1]
                    x1, x2 = int(xs.min()), int(xs.max())
                    y1, y2 = int(ys.min()), int(ys.max())
                    out.append(PrivacyRegion(
                        box=Box(x=x1, y=y1, w=max(1, x2 - x1), h=max(1, y2 - y1)),
                        category=PrivacyCategory.QR_CODE,
                        confidence=0.99,
                        source="opencv:qr",
                        reason="QR code may encode private data or authentication material",
                    ))
        except Exception:
            try:
                _data, pts, _ = self.qr.detectAndDecode(image_bgr)
                if pts is not None:
                    pts = np.array(pts).reshape(-1, 2)
                    xs, ys = pts[:, 0], pts[:, 1]
                    out.append(PrivacyRegion(
                        box=Box(x=int(xs.min()), y=int(ys.min()), w=max(1, int(xs.max()-xs.min())), h=max(1, int(ys.max()-ys.min()))),
                        category=PrivacyCategory.QR_CODE,
                        confidence=0.95,
                        source="opencv:qr",
                        reason="QR code detected",
                    ))
            except Exception:
                pass
        return out

    def _detect_faces(self, image_bgr: np.ndarray) -> list[PrivacyRegion]:
        if self.face is None or image_bgr.size == 0 or self.cv2 is None:
            return []
        gray = self.cv2.cvtColor(image_bgr, self.cv2.COLOR_BGR2GRAY)
        faces = self.face.detectMultiScale(gray, scaleFactor=1.12, minNeighbors=5, minSize=(36, 36))
        return [
            PrivacyRegion(
                box=Box(x=int(x), y=int(y), w=int(w), h=int(h)),
                category=PrivacyCategory.FACE,
                confidence=0.82,
                source="opencv:haar_face",
                reason="Face detected",
            )
            for x, y, w, h in faces
        ]
