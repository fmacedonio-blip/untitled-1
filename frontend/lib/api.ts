const BASE = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";

export type Rect = { x: number; y: number; w: number; h: number };

/** Una zona tal como la define el operario, antes de enrolar. */
export type ZoneSpec = Rect & { name: string };

export type ZoneSummary = {
  name: string;
  rect: Rect;
  base_threshold: number;
  threshold: number;
};

export type Health = {
  ok: boolean;
  device: string;
  grid: number;
  enrolled: boolean;
  samples: number;
  sensitivity: number;
  model: string;
  enrolled_with: string;
  /** El banco se construyó con otro modelo: hay que recalcular los vectores. */
  stale: boolean;
  has_frames: boolean;
  zones: ZoneSummary[];
};

export type EnrollResult = {
  samples: number;
  zones: (ZoneSummary & { patches: number })[];
  sensitivity: number;
  elapsed_ms: number;
};

export type ZoneResult = {
  name: string;
  rect: Rect;
  score: number;
  base_threshold: number;
  threshold: number;
  ratio: number;
  failed: boolean;
  heatmap: string;
};

export type InferResult = {
  verdict: "APROBADO" | "RECHAZADO";
  failed_zones: string[];
  zones: ZoneResult[];
  sensitivity: number;
  elapsed_ms: number;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? "Error del servidor");
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/health"),

  enroll: (images: string[], zones: ZoneSpec[]) =>
    request<EnrollResult>("/enroll", {
      method: "POST",
      body: JSON.stringify({ images, zones }),
    }),

  infer: (image: string) =>
    request<InferResult>("/infer", {
      method: "POST",
      body: JSON.stringify({ image }),
    }),

  setSensitivity: (sensitivity: number) =>
    request<{ sensitivity: number; zones: ZoneSummary[] }>("/config", {
      method: "PUT",
      body: JSON.stringify({ sensitivity }),
    }),

  reembed: () =>
    request<{
      from_model: string;
      to_model: string;
      samples: number;
      zones: ZoneSummary[];
      elapsed_ms: number;
    }>("/reembed", { method: "POST" }),

  reset: () => request<{ enrolled: boolean }>("/reset", { method: "POST" }),
};
