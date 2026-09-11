"use client";

import { useEffect, useState } from "react";
import { api, type Health, type InferResult, type Roi } from "@/lib/api";
import { useCamera } from "@/lib/useCamera";
import { RoiSelector } from "@/components/RoiSelector";

export default function Page() {
  const { videoRef, capture, ready, error, resolution } = useCamera();
  const [roi, setRoi] = useState<Roi | null>(null);
  const [shots, setShots] = useState<string[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [result, setResult] = useState<InferResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const refresh = () => api.health().then(setHealth).catch(() => setHealth(null));

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (health?.roi && !roi) setRoi(health.roi);
  }, [health]);

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

  return (
    <main className="mx-auto max-w-6xl p-6 font-mono text-sm">
      <h1 className="mb-1 text-xl font-bold">EdgeQA — verificación</h1>
      <p className="mb-4 text-muted">
        Pantalla cruda del gate. La interfaz operativa viene después.
      </p>

      {error && (
        <p className="mb-4 rounded border border-red-900 bg-red-950 p-3 text-red-300">
          {error}
        </p>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <div>
          <RoiSelector roi={roi} onChange={setRoi}>
            <video ref={videoRef} playsInline muted className="w-full" />
          </RoiSelector>

          <div className="mt-2 text-xs text-muted">
            cámara: {ready ? resolution : "iniciando…"} · roi:{" "}
            {roi
              ? `${roi.x.toFixed(2)},${roi.y.toFixed(2)} ${roi.w.toFixed(2)}x${roi.h.toFixed(2)}`
              : "sin definir"}
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            <button
              className="rounded bg-neutral-200 px-3 py-2 font-medium text-neutral-900 disabled:opacity-30"
              disabled={!ready || busy || shots.length >= 15}
              onClick={() => {
                const shot = capture();
                if (shot) setShots((s) => [...s, shot]);
              }}
            >
              Capturar ({shots.length}/15)
            </button>

            <button
              className="rounded bg-emerald-600 px-3 py-2 font-medium text-white disabled:opacity-30"
              disabled={busy || shots.length < 8}
              onClick={() =>
                run(async () => {
                  const r = await api.enroll(shots, roi);
                  setMsg(
                    `Enrolado: ${r.samples} muestras, ${r.patches} parches, ` +
                      `umbral base ${r.base_threshold.toFixed(4)} (${r.elapsed_ms} ms)`,
                  );
                  setShots([]);
                  await refresh();
                })
              }
            >
              Enrolar
            </button>

            <button
              className="rounded bg-sky-600 px-3 py-2 font-medium text-white disabled:opacity-30"
              disabled={busy || !health?.enrolled}
              onClick={() =>
                run(async () => {
                  const shot = capture();
                  if (!shot) throw new Error("No se pudo capturar");
                  setResult(await api.infer(shot, roi));
                  await refresh();
                })
              }
            >
              Inspeccionar
            </button>

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

        <div>
          {result ? (
            <>
              <div
                className={`rounded p-6 text-center text-3xl font-bold tracking-wide text-white ${
                  result.verdict === "APROBADO" ? "bg-emerald-600" : "bg-red-600"
                }`}
              >
                {result.verdict}
              </div>

              {/* Los tres números del gate, grandes para anotarlos de un vistazo. */}
              <div className="mt-3 grid grid-cols-3 gap-2">
                <Metric label="score" value={result.score.toFixed(4)} />
                <Metric label="umbral" value={result.threshold.toFixed(4)} />
                <Metric
                  label="ratio"
                  value={`${(result.score / result.threshold).toFixed(2)}x`}
                  accent={
                    result.verdict === "APROBADO" ? "text-emerald-400" : "text-red-400"
                  }
                />
              </div>

              <div className="mt-2 text-xs text-muted">
                umbral base {result.base_threshold.toFixed(4)} · sensibilidad{" "}
                {result.sensitivity.toFixed(2)} · {result.elapsed_ms} ms
              </div>

              <img
                src={result.heatmap}
                alt="mapa de calor"
                className="mt-3 w-full rounded border border-line"
              />
            </>
          ) : (
            <div className="rounded border border-line bg-surface p-6 text-center text-muted">
              Sin inspecciones todavía
            </div>
          )}

          {msg && (
            <p className="mt-3 rounded border border-amber-900 bg-amber-950 p-3 text-amber-200">
              {msg}
            </p>
          )}

          <pre className="mt-3 overflow-x-auto rounded border border-line bg-surface p-3 text-xs text-muted">
            {health ? JSON.stringify(health, null, 2) : "backend no disponible en :8000"}
          </pre>
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
    <div className="rounded border border-line bg-surface p-3">
      <div className="text-xs text-muted">{label}</div>
      <div className={`mt-1 text-lg font-bold tabular-nums ${accent ?? ""}`}>{value}</div>
    </div>
  );
}
