"""API de la estación de inspección.

Tres operaciones: enrolar la pieza de referencia, inspeccionar una pieza nueva
y ajustar la sensibilidad. Todo el estado vive en memoria del proceso y se
persiste a disco tras cada enrolamiento.

La estación se configura con una o más zonas de inspección. Cada zona se
recorta de la misma captura, se evalúa por separado contra su propio banco y
aporta su veredicto al resultado agregado de la pieza.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .bank import DEFAULT_SENSITIVITY, MARGIN, PERCENTILE, Station, Zone
from .embedder import PatchEmbedder
from .imaging import crop_rect, decode_data_url, render_heatmap

BANK_PATH = Path(__file__).resolve().parent.parent / "storage" / "bank.pkl"
MIN_SAMPLES = 8
MAX_SAMPLES = 15

app = FastAPI(title="EdgeQA")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

embedder: PatchEmbedder | None = None
station: Station = Station()


class ZoneSpec(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    x: float
    y: float
    w: float
    h: float

    def rect(self) -> dict:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


class EnrollRequest(BaseModel):
    images: list[str] = Field(min_length=1)
    zones: list[ZoneSpec] = Field(min_length=1)


class InferRequest(BaseModel):
    image: str


class ConfigRequest(BaseModel):
    sensitivity: float = Field(ge=0.1, le=3.0)


class RecalibrateRequest(BaseModel):
    percentile: float = Field(default=PERCENTILE, ge=50.0, le=100.0)
    margin: float = Field(default=MARGIN, ge=1.0, le=2.0)


def get_embedder() -> PatchEmbedder:
    global embedder
    if embedder is None:
        embedder = PatchEmbedder()
    return embedder


def zone_summary(zone: Zone) -> dict:
    scores = sorted(zone.loo_scores)
    return {
        "name": zone.name,
        "rect": zone.rect,
        "base_threshold": zone.base_threshold,
        "threshold": zone.threshold(station.sensitivity),
        "loo_scores": scores,
        "loo_min": scores[0] if scores else 0.0,
        "loo_median": float(np.median(scores)) if scores else 0.0,
        "loo_max": scores[-1] if scores else 0.0,
    }


@app.on_event("startup")
def startup() -> None:
    """Carga el modelo y recupera la estación de una sesión anterior si existe."""
    global station
    get_embedder()
    restored = Station.load(BANK_PATH)
    if restored is not None:
        station = restored


@app.get("/health")
def health() -> dict:
    emb = get_embedder()
    return {
        "ok": True,
        "device": emb.device,
        "grid": emb.grid,
        "enrolled": station.is_ready,
        "samples": station.samples,
        "sensitivity": station.sensitivity,
        "model": emb.model_id,
        "enrolled_with": station.model_id,
        "stale": bool(station.zones) and station.model_id != emb.model_id,
        "has_frames": bool(station.frames),
        "zones": [zone_summary(z) for z in station.zones],
    }


@app.post("/enroll")
def enroll(req: EnrollRequest) -> dict:
    """Construye un banco por zona a partir de capturas de piezas correctas."""
    if len(req.images) < MIN_SAMPLES:
        raise HTTPException(
            status_code=400,
            detail=f"Se necesitan al menos {MIN_SAMPLES} capturas, llegaron {len(req.images)}.",
        )
    if len(req.images) > MAX_SAMPLES:
        raise HTTPException(
            status_code=400,
            detail=f"El máximo es {MAX_SAMPLES} capturas, llegaron {len(req.images)}.",
        )

    names = [z.name for z in req.zones]
    if len(set(names)) != len(names):
        raise HTTPException(status_code=400, detail="Hay zonas con el nombre repetido.")

    emb = get_embedder()
    started = time.time()

    # Las capturas se decodifican una sola vez y se recortan por cada zona:
    # todas las zonas describen la misma pieza en el mismo instante.
    frames = [decode_data_url(img) for img in req.images]

    global station
    station = Station(
        sensitivity=station.sensitivity,
        frames=req.images,
        model_id=emb.model_id,
        image_size=emb.image_size,
    )
    for spec in req.zones:
        rect = spec.rect()
        samples = [emb.embed(crop_rect(frame, rect)) for frame in frames]
        zone = Zone(name=spec.name, rect=rect)
        zone.build(samples, grid=emb.grid)
        station.zones.append(zone)

    station.save(BANK_PATH)

    return {
        "samples": len(frames),
        "zones": [
            {**zone_summary(z), "patches": int(z.patches.shape[0])} for z in station.zones
        ],
        "sensitivity": station.sensitivity,
        "elapsed_ms": round((time.time() - started) * 1000),
    }


@app.post("/infer")
def infer(req: InferRequest) -> dict:
    """Evalúa todas las zonas de una captura y agrega el veredicto."""
    if not station.is_ready:
        raise HTTPException(status_code=409, detail="Todavía no hay ninguna pieza enrolada.")

    emb = get_embedder()
    started = time.time()
    frame = decode_data_url(req.image)

    results = []
    for zone in station.zones:
        cropped = crop_rect(frame, zone.rect)
        score, distances = zone.score(emb.embed(cropped))
        threshold = zone.threshold(station.sensitivity)
        results.append(
            {
                "name": zone.name,
                "rect": zone.rect,
                "score": score,
                "base_threshold": zone.base_threshold,
                "threshold": threshold,
                "ratio": score / threshold if threshold else 0.0,
                "failed": score > threshold,
                "heatmap": render_heatmap(cropped, distances, zone.grid),
            }
        )

    failed = [r["name"] for r in results if r["failed"]]

    return {
        # Una sola pieza fuera de tolerancia en cualquier zona alcanza para
        # rechazarla: las zonas son criterios independientes, no promediables.
        "verdict": "RECHAZADO" if failed else "APROBADO",
        "failed_zones": failed,
        "zones": results,
        "sensitivity": station.sensitivity,
        "elapsed_ms": round((time.time() - started) * 1000),
    }


@app.get("/config")
def get_config() -> dict:
    return {
        "sensitivity": station.sensitivity,
        "enrolled": station.is_ready,
        "zones": [zone_summary(z) for z in station.zones],
    }


@app.put("/config")
def put_config(req: ConfigRequest) -> dict:
    """Ajusta la sensibilidad sin necesidad de volver a enrolar."""
    station.sensitivity = req.sensitivity
    if station.is_ready:
        station.save(BANK_PATH)
    return {
        "sensitivity": station.sensitivity,
        "zones": [zone_summary(z) for z in station.zones],
    }


@app.post("/reembed")
def reembed() -> dict:
    """Recalcula los embeddings sobre las capturas de enrolamiento guardadas.

    Cambiar de modelo o de tamaño de entrada invalida los vectores del banco,
    pero no las fotos: se vuelven a procesar las mismas capturas y la estación
    queda lista sin repetir la sesión de enrolamiento.
    """
    if not station.frames:
        raise HTTPException(
            status_code=409,
            detail="No hay capturas guardadas. Hay que enrolar de nuevo.",
        )

    emb = get_embedder()
    started = time.time()
    frames = [decode_data_url(img) for img in station.frames]

    previous = station.model_id or "desconocido"
    for zone in station.zones:
        samples = [emb.embed(crop_rect(frame, zone.rect)) for frame in frames]
        zone.build(samples, grid=emb.grid)

    station.model_id = emb.model_id
    station.image_size = emb.image_size
    station.save(BANK_PATH)

    return {
        "from_model": previous,
        "to_model": emb.model_id,
        "samples": len(frames),
        "zones": [zone_summary(z) for z in station.zones],
        "elapsed_ms": round((time.time() - started) * 1000),
    }


@app.post("/recalibrate")
def recalibrate(req: RecalibrateRequest) -> dict:
    """Recalcula los umbrales sobre el enrolamiento existente.

    Los scores de leave-one-out ya están guardados, de modo que cambiar el
    criterio de calibración no obliga a volver a capturar la pieza.
    """
    if not station.is_ready:
        raise HTTPException(status_code=409, detail="Todavía no hay ninguna pieza enrolada.")

    for zone in station.zones:
        zone.calibrate(req.percentile, req.margin)
    station.save(BANK_PATH)

    return {
        "percentile": req.percentile,
        "margin": req.margin,
        "zones": [zone_summary(z) for z in station.zones],
    }


@app.post("/reset")
def reset() -> dict:
    """Descarta el enrolamiento actual."""
    global station
    station = Station(sensitivity=station.sensitivity)
    BANK_PATH.unlink(missing_ok=True)
    return {"enrolled": False}
