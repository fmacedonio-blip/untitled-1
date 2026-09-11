"""Extracción de embeddings por parche con DINOv2.

La pieza clave del sistema: convertir una imagen en una grilla de vectores,
cada uno describiendo una región pequeña. Ver design.md, sección
"embeddings por parche, no vector global".
"""
from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

MODEL_ID = "facebook/dinov2-small"
IMAGE_SIZE = 518  # múltiplo de 14 (tamaño de parche de DINOv2)


def _pick_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


class PatchEmbedder:
    """Envuelve DINOv2 y devuelve la grilla de embeddings de una imagen."""

    def __init__(self, image_size: int = IMAGE_SIZE) -> None:
        self.device = _pick_device()
        self.image_size = image_size
        self.processor = AutoImageProcessor.from_pretrained(
            MODEL_ID,
            size={"height": image_size, "width": image_size},
            crop_size={"height": image_size, "width": image_size},
            do_center_crop=False,
        )
        self.model = AutoModel.from_pretrained(MODEL_ID).to(self.device).eval()
        self.grid = image_size // 14

    @torch.inference_mode()
    def embed(self, image: Image.Image) -> np.ndarray:
        """Devuelve los parches de una imagen como (n_parches, dims), normalizados L2."""
        inputs = self.processor(images=image.convert("RGB"), return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        out = self.model(**inputs).last_hidden_state  # (1, 1 + n_parches, dims)

        patches = out[0, 1:]  # descartamos el token CLS: solo queremos lo local
        patches = torch.nn.functional.normalize(patches, dim=-1)
        return patches.cpu().numpy().astype(np.float32)
