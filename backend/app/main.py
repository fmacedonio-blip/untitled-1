"""API de la estación de inspección.

Tres operaciones: enrolar la pieza de referencia, inspeccionar una pieza nueva
y ajustar la sensibilidad. Todo el estado vive en memoria del proceso y se
persiste a disco tras cada enrolamiento.
"""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .bank import DEFAULT_SENSITIVITY, MemoryBank
from .embedder import PatchEmbedder
from .imaging import crop_roi, decode_data_url, render_heatmap

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
bank: MemoryBank = MemoryBank()


class Roi(BaseModel):
    x: float
    y: float
    w: float
    h: float


class EnrollRequest(BaseModel):
    images: list[str] = Field(min_length=1)
    roi: Roi | None = None


class InferRequest(BaseModel):
    image: str
    roi: Roi | None = None


class ConfigRequest(BaseModel):
    sensitivity: float = Field(ge=0.5, le=3.0)


def get_embedder() -> PatchEmbedder:
    global embedder
    if embedder is None:
        embedder = PatchEmbedder()
    return embedder


@app.on_event("startup")
def startup() -> None:
    """Carga el modelo y recupera el banco de una sesión anterior si existe."""
    global bank
    get_embedder()
    restored = MemoryBank.load(BANK_PATH)
    if restored is not None:
        bank = restored


@app.get("/health")
def health() -> dict:
    emb = get_embedder()
    return {
        "ok": True,
        "device": emb.device,
        "grid": emb.grid,
        "enrolled": bank.is_ready,
        "samples": len(bank.per_sample),
        "base_threshold": bank.base_threshold,
        "sensitivity": bank.sensitivity,
        "threshold": bank.threshold,
        "roi": bank.roi,
    }


@app.post("/enroll")
def enroll(req: EnrollRequest) -> dict:
    """Construye el banco de memoria a partir de capturas de piezas correctas."""
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

    emb = get_embedder()
    roi = req.roi.model_dump() if req.roi else None

    started = time.time()
    samples = [emb.embed(crop_roi(decode_data_url(img), roi)) for img in req.images]

    global bank
    bank = MemoryBank(sensitivity=bank.sensitivity)
    bank.build(samples, grid=emb.grid, roi=roi)
    bank.save(BANK_PATH)

    return {
        "samples": len(samples),
        "patches": int(bank.patches.shape[0]),
        "base_threshold": bank.base_threshold,
        "threshold": bank.threshold,
        "sensitivity": bank.sensitivity,
        "elapsed_ms": round((time.time() - started) * 1000),
    }


@app.post("/infer")
def infer(req: InferRequest) -> dict:
    """Evalúa una pieza y devuelve veredicto, score y heatmap."""
    if not bank.is_ready:
        raise HTTPException(status_code=409, detail="Todavía no hay ninguna pieza enrolada.")

    emb = get_embedder()
    roi = req.roi.model_dump() if req.roi else bank.roi

    started = time.time()
    cropped = crop_roi(decode_data_url(req.image), roi)
    patches = emb.embed(cropped)
    score, distances = bank.score(patches)
    heatmap = render_heatmap(cropped, distances, bank.grid)

    return {
        "verdict": "RECHAZADO" if score > bank.threshold else "APROBADO",
        "score": score,
        "threshold": bank.threshold,
        "base_threshold": bank.base_threshold,
        "sensitivity": bank.sensitivity,
        "ratio": score / bank.base_threshold if bank.base_threshold else 0.0,
        "heatmap": heatmap,
        "elapsed_ms": round((time.time() - started) * 1000),
    }


@app.get("/config")
def get_config() -> dict:
    return {
        "sensitivity": bank.sensitivity,
        "base_threshold": bank.base_threshold,
        "threshold": bank.threshold,
        "enrolled": bank.is_ready,
    }


@app.put("/config")
def put_config(req: ConfigRequest) -> dict:
    """Ajusta la sensibilidad sin necesidad de volver a enrolar."""
    bank.sensitivity = req.sensitivity
    if bank.is_ready:
        bank.save(BANK_PATH)
    return {
        "sensitivity": bank.sensitivity,
        "base_threshold": bank.base_threshold,
        "threshold": bank.threshold,
    }


@app.post("/reset")
def reset() -> dict:
    """Descarta el enrolamiento actual."""
    global bank
    keep = bank.sensitivity
    bank = MemoryBank(sensitivity=keep)
    BANK_PATH.unlink(missing_ok=True)
    return {"enrolled": False}
