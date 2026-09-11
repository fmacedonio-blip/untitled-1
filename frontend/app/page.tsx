"use client";

import { useEffect, useState } from "react";
import {
  api,
  type Health,
  type InferResult,
  type Rect,
  type ZoneSpec,
} from "@/lib/api";
import { useCamera } from "@/lib/useCamera";
import { ZoneEditor, zoneColor } from "@/components/ZoneEditor";

export default function Page() {
  const { videoRef, capture, ready, error, resolution } = useCamera();
  const [zones, setZones] = useState<ZoneSpec[]>([]);
  const [shots, setShots] = useState<string[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [result, setResult] = useState<InferResult | null>(null);
  const [sensitivity, setSensitivity] = useState(1.0);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const refresh = () => api.health().then(setHealth).catch(() => setHealth(null));

  useEffect(() => {
    refresh();
  }, []);

  // Al recuperar una estación enrolada, sus zonas mandan sobre lo dibujado.
  useEffect(() => {
    if (!health) return;
    setSensitivity(health.sensitivity);
    if (health.enrolled && health.zones.length) {
      setZones(health.zones.map((z) => ({ name: z.name, ...z.rect })));
    }
  }, [health]);

  const enrolled = health?.enrolled ?? false;

  // El umbral es lineal en la sensibilidad, así que los veredictos por zona
  // se recalculan en pantalla sin volver a capturar ni consultar al backend.
  const zoneVerdicts = result?.zones.map((z) => ({
    ...z,
    liveThreshold: z.base_threshold * sensitivity,
    liveFailed: z.score > z.base_threshold * sensitivity,
  }));
  const verdict = zoneVerdicts
    ? zoneVerdicts.some((z) => z.liveFailed)
      ? "RECHAZADO"
      : "APROBADO"
    : null;

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Error inesperado");
    } finally {
      setBusy(false);
    }
  };

  const addZone = (rect: Rect) => {
    const name =
      zones.length === 0 ? "pieza" : `zona ${zones.length + 1}`;
    setZones((z) => [...z, { name, ...rect }]);
  };

  return (
    <main className="mx-auto max-w-7xl p-4 font-mono text-xs">
      <h1 className="mb-1 text-base font-bold">EdgeQA — estación de inspección</h1>
      <p className="mb-3 text-muted">
        Definí las zonas, enrolá piezas correctas e inspeccioná.
      </p>

      {error && (
        <p className="mb-4 rounded border border-red-900 bg-red-950 p-3 text-red-300">
          {error}
        </p>
      )}

      {msg && (
        <p className="mb-4 rounded border border-amber-900 bg-amber-950 p-3 text-amber-200">
          {msg}
        </p>
      )}

      <div className={`grid gap-6 ${enrolled ? "md:grid-cols-2" : ""}`}>
        <div className={enrolled ? "" : "mx-auto w-full max-w-3xl"}>
          <ZoneEditor zones={zones} onAdd={addZone} locked={enrolled}>
            <video ref={videoRef} playsInline muted className="w-full" />
          </ZoneEditor>

          {health?.stale && (
            <p className="mt-2 rounded border border-amber-800 bg-amber-950 p-2 text-amber-200">
              El banco se enroló con {health.enrolled_with || "otro modelo"} y ahora
              corre {health.model}.{" "}
              {health.has_frames
                ? "Recalculá los vectores sobre las capturas guardadas."
                : "Hay que enrolar de nuevo."}
            </p>
          )}

          <div className="mt-2 text-xs text-muted">
            cámara: {ready ? resolution : "iniciando…"} · {zones.length}{" "}
            {zones.length === 1 ? "zona" : "zonas"}
            {enrolled && " · enrolada (bloqueada)"}
          </div>

          {/* Lista de zonas: renombrar y borrar mientras no haya enrolamiento. */}
          {zones.length > 0 && (
            <div className="mt-3 space-y-1">
              {zones.map((zone, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 rounded border border-line bg-surface px-2 py-1"
                >
                  <span
                    className="h-3 w-3 shrink-0 rounded-sm"
                    style={{ background: zoneColor(i) }}
                  />
                  <input
                    value={zone.name}
                    disabled={enrolled}
                    className="flex-1 bg-transparent outline-none disabled:text-muted"
                    onChange={(e) =>
                      setZones((zs) =>
                        zs.map((z, j) =>
                          j === i ? { ...z, name: e.target.value } : z,
                        ),
                      )
                    }
                  />
                  <span className="text-xs text-muted">
                    {(zone.w * 100).toFixed(0)}x{(zone.h * 100).toFixed(0)}
                  </span>
                  {!enrolled && (
                    <button
                      className="px-1 text-muted hover:text-red-400"
                      title="Quitar zona"
                      onClick={() =>
                        setZones((zs) => zs.filter((_, j) => j !== i))
                      }
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="mt-3 flex flex-wrap gap-2">
            <button
              className="rounded bg-neutral-200 px-3 py-2 font-medium text-neutral-900 disabled:opacity-30"
              disabled={!ready || busy || enrolled || shots.length >= 15}
              onClick={() => {
                const shot = capture();
                if (shot) setShots((s) => [...s, shot]);
              }}
            >
              Capturar ({shots.length}/15)
            </button>

            <button
              className="rounded bg-emerald-600 px-3 py-2 font-medium text-white disabled:opacity-30"
              disabled={busy || shots.length < 8 || zones.length === 0}
              onClick={() =>
                run(async () => {
                  const r = await api.enroll(shots, zones);
                  setMsg(
                    `Enrolado: ${r.samples} muestras en ${r.zones.length} ` +
                      `${r.zones.length === 1 ? "zona" : "zonas"} (${r.elapsed_ms} ms) · ` +
                      r.zones
                        .map((z) => `${z.name} ${z.base_threshold.toFixed(4)}`)
                        .join(" · "),
                  );
                  setShots([]);
                  setResult(null);
                  await refresh();
                })
              }
            >
              Enrolar
            </button>

            <button
              className="rounded bg-sky-600 px-3 py-2 font-medium text-white disabled:opacity-30"
              disabled={busy || !enrolled}
              onClick={() =>
                run(async () => {
                  const shot = capture();
                  if (!shot) throw new Error("No se pudo capturar");
                  setResult(await api.infer(shot));
                })
              }
            >
              Inspeccionar
            </button>

            {health?.stale && health.has_frames && (
              <button
                className="rounded bg-amber-600 px-3 py-2 font-medium text-white disabled:opacity-30"
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    const r = await api.reembed();
                    setMsg(
                      `Recalculado con ${r.to_model} sobre ${r.samples} capturas ` +
                        `guardadas (${r.elapsed_ms} ms) · ` +
                        r.zones
                          .map((z) => `${z.name} ${z.base_threshold.toFixed(4)}`)
                          .join(" · "),
                    );
                    setResult(null);
                    await refresh();
                  })
                }
              >
                Recalcular con {health.model.split("/").pop()}
              </button>
            )}

            <button
              className="rounded border border-line px-3 py-2 text-muted disabled:opacity-30"
              disabled={busy}
              onClick={() =>
                run(async () => {
                  await api.reset();
                  setShots([]);
                  setResult(null);
                  await refresh();
                })
              }
            >
              Reiniciar
            </button>
          </div>

          {enrolled && (
            <div className="mt-4 rounded border border-line bg-surface p-3">
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-muted">sensibilidad</span>
                <span className="font-bold tabular-nums">
                  {sensitivity.toFixed(2)}
                </span>
              </div>
              <input
                type="range"
                min={0.5}
                max={2}
                step={0.05}
                value={sensitivity}
                className="mt-2 w-full accent-sky-500"
                onChange={(e) => setSensitivity(Number(e.target.value))}
                onPointerUp={() =>
                  run(async () => {
                    await api.setSensitivity(sensitivity);
                    await refresh();
                  })
                }
              />
              <div className="mt-1 flex justify-between text-xs text-muted">
                <span>estricto</span>
                <span>permisivo</span>
              </div>
            </div>
          )}

          {shots.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {shots.map((s, i) => (
                <img
                  key={i}
                  src={s}
                  alt=""
                  className="h-12 w-16 cursor-pointer rounded object-cover ring-1 ring-line hover:ring-red-500"
                  title="Clic para descartar"
                  onClick={() => setShots((prev) => prev.filter((_, j) => j !== i))}
                />
              ))}
            </div>
          )}
        </div>

        <div className={enrolled ? "" : "hidden"}>
          {zoneVerdicts ? (
            <>
              <div
                className={`rounded p-3 text-center text-2xl font-bold tracking-wide text-white ${
                  verdict === "APROBADO" ? "bg-emerald-600" : "bg-red-600"
                }`}
              >
                {verdict}
              </div>

              {verdict === "RECHAZADO" && (
                <p className="mt-2 text-center text-red-400">
                  falla en:{" "}
                  {zoneVerdicts
                    .filter((z) => z.liveFailed)
                    .map((z) => z.name)
                    .join(", ")}
                </p>
              )}

              <div className="mt-2 text-xs text-muted">
                {result!.elapsed_ms} ms · {zoneVerdicts.length} zonas
              </div>

              <div className="mt-2 grid grid-cols-2 gap-2">
                {zoneVerdicts.map((zone, i) => (
                  <div
                    key={zone.name}
                    className={`rounded border p-3 ${
                      zone.liveFailed
                        ? "border-red-700 bg-red-950/40"
                        : "border-line bg-surface"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="h-3 w-3 rounded-sm"
                        style={{ background: zoneColor(i) }}
                      />
                      <span className="font-bold">{zone.name}</span>
                      <span
                        className={`ml-auto text-xs font-bold ${
                          zone.liveFailed ? "text-red-400" : "text-emerald-400"
                        }`}
                      >
                        {zone.liveFailed ? "FUERA DE TOLERANCIA" : "OK"}
                      </span>
                    </div>

                    <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                      <Metric label="score" value={zone.score.toFixed(4)} />
                      <Metric
                        label="umbral"
                        value={zone.liveThreshold.toFixed(4)}
                      />
                      <Metric
                        label="ratio"
                        value={`${(zone.score / zone.liveThreshold).toFixed(2)}x`}
                        accent={
                          zone.liveFailed ? "text-red-400" : "text-emerald-400"
                        }
                      />
                    </div>

                    <img
                      src={zone.heatmap}
                      alt={`mapa de calor de ${zone.name}`}
                      className="mt-2 max-h-48 w-full rounded border border-line object-contain"
                    />
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="rounded border border-line bg-surface p-6 text-center text-muted">
              Sin inspecciones todavía
            </div>
          )}

        </div>
      </div>
    </main>
  );
}

function Metric({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div className="rounded border border-line bg-background p-2">
      <div className="text-xs text-muted">{label}</div>
      <div className={`mt-1 font-bold tabular-nums ${accent ?? ""}`}>{value}</div>
    </div>
  );
}
