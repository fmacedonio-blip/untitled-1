"""Decodificación de capturas, recorte por ROI y generación del heatmap."""
from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image

HEATMAP_ALPHA = 0.55


def decode_data_url(data_url: str) -> Image.Image:
    """Convierte un data URL (o base64 pelado) en una imagen PIL."""
    payload = data_url.split(",", 1)[-1] if "," in data_url else data_url
    raw = base64.b64decode(payload)
    return Image.open(io.BytesIO(raw)).convert("RGB")


def crop_roi(image: Image.Image, roi: dict | None) -> Image.Image:
    """Recorta la región de interés.

    El ROI llega en coordenadas relativas (0..1) para no depender de la
    resolución con la que el navegador entregó el cuadro.
    """
    if not roi:
        return image

    w, h = image.size
    left = int(max(0.0, min(1.0, roi["x"])) * w)
    top = int(max(0.0, min(1.0, roi["y"])) * h)
    right = int(max(0.0, min(1.0, roi["x"] + roi["w"])) * w)
    bottom = int(max(0.0, min(1.0, roi["y"] + roi["h"])) * h)

    if right - left < 10 or bottom - top < 10:
        return image
    return image.crop((left, top, right, bottom))


def _colorize(norm: np.ndarray) -> np.ndarray:
    """Rampa de color tipo 'inferno' simplificada: oscuro -> rojo -> amarillo."""
    stops = np.array(
        [
            [0, 0, 40],
            [90, 20, 110],
            [200, 50, 80],
            [250, 130, 30],
            [255, 240, 150],
        ],
        dtype=np.float32,
    )
    positions = np.linspace(0.0, 1.0, len(stops))
    out = np.zeros((*norm.shape, 3), dtype=np.float32)
    for channel in range(3):
        out[..., channel] = np.interp(norm, positions, stops[:, channel])
    return out


def render_heatmap(base: Image.Image, distances: np.ndarray, grid: int) -> str:
    """Superpone el mapa de anomalía sobre la pieza y lo devuelve como data URL.

    El mapa llega como una grilla de 37x37 y se escala bilinealmente al tamaño
    de la imagen, que es lo que lo vuelve legible para el operario.
    """
    grid_map = distances.reshape(grid, grid)

    lo, hi = float(grid_map.min()), float(grid_map.max())
    norm = (grid_map - lo) / (hi - lo) if hi > lo else np.zeros_like(grid_map)

    heat = Image.fromarray((norm * 255).astype(np.uint8), mode="L")
    heat = heat.resize(base.size, Image.BILINEAR)
    norm_full = np.asarray(heat, dtype=np.float32) / 255.0

    colored = _colorize(norm_full)
    original = np.asarray(base, dtype=np.float32)

    # La intensidad de la mezcla sigue al propio mapa: las zonas normales
    # quedan casi intactas y solo se tiñe lo que se aparta.
    alpha = (norm_full * HEATMAP_ALPHA)[..., None]
    blended = original * (1 - alpha) + colored * alpha

    result = Image.fromarray(blended.clip(0, 255).astype(np.uint8))
    buffer = io.BytesIO()
    result.save(buffer, format="JPEG", quality=88)
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/jpeg;base64,{encoded}"
