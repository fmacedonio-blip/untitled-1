const BASE = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";

export type Roi = { x: number; y: number; w: number; h: number };

export type Health = {
  ok: boolean;
  device: string;
  grid: number;
  enrolled: boolean;
  samples: number;
  base_threshold: number;
  sensitivity: number;
  threshold: number;
  roi: Roi | null;
};

export type EnrollResult = {
  samples: number;
  patches: number;
  base_threshold: number;
  threshold: number;
  sensitivity: number;
  elapsed_ms: number;
};

export type InferResult = {
  verdict: "APROBADO" | "RECHAZADO";
  score: number;
  threshold: number;
  base_threshold: number;
  sensitivity: number;
  ratio: number;
  heatmap: string;
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

  enroll: (images: string[], roi: Roi | null) =>
    request<EnrollResult>("/enroll", {
      method: "POST",
      body: JSON.stringify({ images, roi }),
    }),

  infer: (image: string, roi: Roi | null) =>
    request<InferResult>("/infer", {
      method: "POST",
      body: JSON.stringify({ image, roi }),
    }),

  setSensitivity: (sensitivity: number) =>
    request<{ sensitivity: number; base_threshold: number; threshold: number }>(
      "/config",
      { method: "PUT", body: JSON.stringify({ sensitivity }) },
    ),

  reset: () => request<{ enrolled: boolean }>("/reset", { method: "POST" }),
};
