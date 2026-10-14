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
    # Upscale tiny synthetic fixtures; leave clinical-resolution CT as-is
    longest = max(image.size)
    if longest < 256:
        scale = max(1, 512 // longest)
        image = image.resize(
            (image.width * scale, image.height * scale),
            Image.Resampling.NEAREST,
        )
    elif longest > 1024:
        # Cap huge matrices for snappy browser demos
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
