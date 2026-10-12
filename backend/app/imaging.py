"""Slice rendering helpers (window/level → PNG)."""

from __future__ import annotations

import io

import numpy as np
from numpy.typing import NDArray
from PIL import Image


def apply_window(
    slice_hu: NDArray[np.floating],
    center: float = 40.0,
    width: float = 400.0,
) -> NDArray[np.uint8]:
    """Map HU values to 8-bit grayscale with a CT window."""
    lo = center - width / 2.0
    hi = center + width / 2.0
    clipped = np.clip(np.asarray(slice_hu, dtype=np.float64), lo, hi)
    if hi <= lo:
        return np.zeros(clipped.shape, dtype=np.uint8)
    norm = (clipped - lo) / (hi - lo)
    return (norm * 255.0).astype(np.uint8)


def slice_to_png_bytes(
    slice_hu: NDArray[np.floating],
    center: float = 40.0,
    width: float = 400.0,
) -> bytes:
    pixels = apply_window(slice_hu, center=center, width=width)
    image = Image.fromarray(pixels, mode="L")
    # Upscale tiny fixtures so the browser demo is visible
    if max(image.size) < 256:
        scale = max(1, 256 // max(image.size))
        image = image.resize((image.width * scale, image.height * scale), Image.NEAREST)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
