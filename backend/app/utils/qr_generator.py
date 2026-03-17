from __future__ import annotations

import base64
from io import BytesIO

import qrcode


def generate_qr_code_base64(payload: str) -> str:
    qr_image = qrcode.make(payload)
    buffer = BytesIO()
    qr_image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
