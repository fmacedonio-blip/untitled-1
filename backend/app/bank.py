"""Bancos de memoria por zona y cálculo de anomalía.

Enfoque estilo PatchCore simplificado: se acumulan los parches de todas las
piezas correctas y, para una pieza nueva, cada parche se compara contra el
banco quedándose con la distancia a su vecino más cercano.

Cada zona de inspección tiene su propio banco y su propio umbral, de modo
que una región pequeña se calibra contra su propia varianza y no contra la
de la pieza entera. Ver design.md, "zonas de inspección múltiples".
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

TOP_K = 5  # cuántos parches peores promediamos para el score
DEFAULT_SENSITIVITY = 1.0
PERCENTILE = 95.0  # percentil de los scores de enrolamiento que fija el umbral
MARGIN = 1.15  # holgura sobre el percentil, para no rechazar piezas sanas
SEARCH_RADIUS = 0  # 0 = búsqueda global; medido sobre capturas reales, restringir
#                    el entorno no redujo la varianza de colocación (ver design.md)


def _neighbourhood_mask(grid: int, radius: int) -> np.ndarray:
    """Para cada posición de la grilla, qué posiciones del banco puede mirar.

    Devuelve una matriz booleana (n_parches, n_parches) donde la fila i marca
    las posiciones que caen dentro de `radius` parches de i, medido sobre la
    grilla bidimensional.
    """
    idx = np.arange(grid * grid)
    rows, cols = idx // grid, idx % grid
    dr = np.abs(rows[:, None] - rows[None, :])
    dc = np.abs(cols[:, None] - cols[None, :])
    return (dr <= radius) & (dc <= radius)


def _scores_against(
    patches: np.ndarray,
    bank: np.ndarray,
    top_k: int = TOP_K,
    grid: int = 0,
    radius: int = SEARCH_RADIUS,
):
    """Distancia de cada parche al más parecido de su vecindario en el banco.

    Los vectores vienen normalizados L2, así que el producto punto es el coseno
    y la distancia es 1 - coseno.

    La comparación se restringe a un entorno espacial: el parche de la posición
    (fila, columna) sólo se mide contra las posiciones del banco a lo sumo
    `radius` parches de distancia, en cualquiera de las muestras enroladas.

    Esto es lo que absorbe la recolocación de la pieza. Un desplazamiento de
    dos milímetros equivale a más de un parche completo a 518px, y sin esta
    tolerancia aparece como anomalía: el parche se compara contra un contenido
    que en la pieza enrolada estaba unas posiciones más allá. Restringir la
    búsqueda al entorno permite encontrar esa correspondencia desplazada sin
    abrir la puerta a que un defecto se empareje con una región lejana que
    casualmente se le parezca.
    """
    similarity = patches @ bank.T  # (n_parches, n_banco)

    if grid and radius > 0 and bank.shape[0] % (grid * grid) == 0:
        n_samples = bank.shape[0] // (grid * grid)
        mask = _neighbourhood_mask(grid, radius)
        # El banco apila las muestras una tras otra: la misma máscara de
        # vecindario vale para cada una de ellas.
        mask = np.tile(mask, (1, n_samples))
        similarity = np.where(mask, similarity, -np.inf)

    nearest = similarity.max(axis=1)
    distances = 1.0 - nearest

    k = min(top_k, distances.shape[0])
    worst = np.partition(distances, -k)[-k:]
    return float(worst.mean()), distances


@dataclass
class Zone:
    """Una región de la pieza con su banco de parches y su umbral propio."""

    name: str
    rect: dict  # x, y, w, h en coordenadas relativas (0..1)
    per_sample: list[np.ndarray] = field(default_factory=list)
    patches: np.ndarray | None = None
    base_threshold: float = 0.0
    loo_scores: list[float] = field(default_factory=list)
    grid: int = 0

    def build(self, samples: list[np.ndarray], grid: int, percentile: float = PERCENTILE) -> None:
        """Acumula los parches y calibra el umbral por leave-one-out.

        Para cada muestra se calcula su score contra el banco formado por todas
        las demás. Los scores quedan guardados para poder recalibrar sin volver
        a capturar.
        """
        self.per_sample = samples
        self.patches = np.concatenate(samples, axis=0)
        self.grid = grid

        scores = []
        for i in range(len(samples)):
            others = [s for j, s in enumerate(samples) if j != i]
            if not others:
                continue
            score, _ = _scores_against(
                samples[i], np.concatenate(others, axis=0), grid=grid
            )
            scores.append(score)

        self.loo_scores = scores
        self.calibrate(percentile)

    def calibrate(
        self, percentile: float = PERCENTILE, margin: float = MARGIN
    ) -> None:
        """Fija el umbral base en un percentil de los scores de enrolamiento.

        Tomar el máximo —la formulación obvia— deja que una sola captura mal
        alineada dicte la tolerancia de toda la zona, y el efecto se agrava en
        zonas pequeñas, donde un desplazamiento de milímetros se amplifica al
        escalar el recorte.

        El percentil descarta esos valores atípicos, pero por sí solo queda
        demasiado ajustado: el enrolamiento describe cómo se parecen entre sí
        las capturas de una misma sesión, y una pieza nueva siempre cae algo
        más lejos que eso. El margen cubre esa diferencia.
        """
        if not self.loo_scores:
            self.base_threshold = 0.0
            return
        self.base_threshold = float(np.percentile(self.loo_scores, percentile)) * margin

    def score(self, patches: np.ndarray):
        return _scores_against(patches, self.patches, grid=self.grid)

    def threshold(self, sensitivity: float) -> float:
        return self.base_threshold * sensitivity


@dataclass
class Station:
    """Configuración completa de la estación: sus zonas y la sensibilidad.

    Junto con los embeddings se conservan las capturas de enrolamiento tal
    como llegaron. Ocupan poco y evitan tener que volver a fotografiar la
    pieza cada vez que cambia el modelo o el tamaño de entrada, que es
    justamente cuando los vectores guardados dejan de servir.
    """

    zones: list[Zone] = field(default_factory=list)
    sensitivity: float = DEFAULT_SENSITIVITY
    frames: list[str] = field(default_factory=list)  # data URLs de las capturas
    model_id: str = ""
    image_size: int = 0

    @property
    def is_ready(self) -> bool:
        return bool(self.zones) and all(z.patches is not None for z in self.zones)

    @property
    def samples(self) -> int:
        return len(self.zones[0].per_sample) if self.zones else 0

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(
                {
                    "sensitivity": self.sensitivity,
                    "frames": self.frames,
                    "model_id": self.model_id,
                    "image_size": self.image_size,
                    "zones": [
                        {
                            "name": z.name,
                            "rect": z.rect,
                            "per_sample": z.per_sample,
                            "base_threshold": z.base_threshold,
                            "loo_scores": z.loo_scores,
                            "grid": z.grid,
                        }
                        for z in self.zones
                    ],
                },
                fh,
            )

    @classmethod
    def load(cls, path: Path) -> "Station | None":
        if not path.exists():
            return None
        try:
            with path.open("rb") as fh:
                data = pickle.load(fh)
        except Exception:
            return None

        # Los bancos guardados por la versión de zona única no se migran:
        # reenrolar cuesta un minuto y evita arrastrar un formato muerto.
        if "zones" not in data:
            return None

        station = cls(
            sensitivity=data.get("sensitivity", DEFAULT_SENSITIVITY),
            frames=data.get("frames", []),
            model_id=data.get("model_id", ""),
            image_size=data.get("image_size", 0),
        )
        for z in data["zones"]:
            zone = Zone(
                name=z["name"],
                rect=z["rect"],
                per_sample=z["per_sample"],
                base_threshold=z["base_threshold"],
                loo_scores=z.get("loo_scores", []),
                grid=z["grid"],
            )
            if zone.per_sample:
                zone.patches = np.concatenate(zone.per_sample, axis=0)
            station.zones.append(zone)
        return station
