"""Banco de memoria de parches normales y cálculo de anomalía.

Enfoque estilo PatchCore simplificado: se acumulan los parches de todas las
piezas correctas y, para una pieza nueva, cada parche se compara contra el
banco quedándose con la distancia a su vecino más cercano.

Ver design.md, secciones "embeddings por parche" y "score por media del top-k".
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

TOP_K = 5  # cuántos parches peores promediamos para el score
DEFAULT_SENSITIVITY = 1.15


def _scores_against(patches: np.ndarray, bank: np.ndarray, top_k: int = TOP_K):
    """Distancia de cada parche a su vecino más cercano del banco.

    Los vectores vienen normalizados L2, así que el producto punto es el coseno
    y la distancia es 1 - coseno. Se devuelve el score agregado y el mapa
    completo, que sirve para el heatmap.
    """
    similarity = patches @ bank.T  # (n_parches, n_banco)
    nearest = similarity.max(axis=1)
    distances = 1.0 - nearest

    k = min(top_k, distances.shape[0])
    worst = np.partition(distances, -k)[-k:]
    return float(worst.mean()), distances


@dataclass
class MemoryBank:
    """Parches normales y el umbral calibrado sobre ellos."""

    patches: np.ndarray | None = None
    per_sample: list[np.ndarray] = field(default_factory=list)
    base_threshold: float = 0.0
    sensitivity: float = DEFAULT_SENSITIVITY
    grid: int = 0
    roi: dict | None = None

    @property
    def is_ready(self) -> bool:
        return self.patches is not None and len(self.per_sample) > 0

    @property
    def threshold(self) -> float:
        return self.base_threshold * self.sensitivity

    def build(self, samples: list[np.ndarray], grid: int, roi: dict | None) -> None:
        """Construye el banco y calibra el umbral por leave-one-out.

        Para cada muestra se calcula su score contra el banco formado por todas
        las demás. El umbral base es el peor de esos scores: el piso por encima
        del cual una pieza deja de parecerse a lo que sabemos que es correcto.
        """
        self.per_sample = samples
        self.patches = np.concatenate(samples, axis=0)
        self.grid = grid
        self.roi = roi

        loo_scores = []
        for i in range(len(samples)):
            others = [s for j, s in enumerate(samples) if j != i]
            if not others:
                continue
            rest = np.concatenate(others, axis=0)
            score, _ = _scores_against(samples[i], rest)
            loo_scores.append(score)

        self.base_threshold = max(loo_scores) if loo_scores else 0.0

    def score(self, patches: np.ndarray):
        """Evalúa una pieza: score agregado y mapa de distancias por parche."""
        if not self.is_ready:
            raise RuntimeError("El banco no está enrolado")
        return _scores_against(patches, self.patches)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(
                {
                    "per_sample": self.per_sample,
                    "base_threshold": self.base_threshold,
                    "sensitivity": self.sensitivity,
                    "grid": self.grid,
                    "roi": self.roi,
                },
                fh,
            )

    @classmethod
    def load(cls, path: Path) -> "MemoryBank | None":
        if not path.exists():
            return None
        try:
            with path.open("rb") as fh:
                data = pickle.load(fh)
        except Exception:
            return None

        bank = cls(
            per_sample=data["per_sample"],
            base_threshold=data["base_threshold"],
            sensitivity=data.get("sensitivity", DEFAULT_SENSITIVITY),
            grid=data.get("grid", 0),
            roi=data.get("roi"),
        )
        if bank.per_sample:
            bank.patches = np.concatenate(bank.per_sample, axis=0)
        return bank
