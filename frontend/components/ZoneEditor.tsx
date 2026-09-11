"use client";

import { useRef, useState } from "react";
import type { Rect, ZoneSpec } from "@/lib/api";

type Props = {
  zones: ZoneSpec[];
  onAdd: (rect: Rect) => void;
  locked: boolean;
  children: React.ReactNode;
};

/** Colores por posición, para distinguir las zonas de un vistazo. */
export const ZONE_COLORS = [
  "#38bdf8",
  "#f472b6",
  "#a3e635",
  "#fbbf24",
  "#c084fc",
  "#fb7185",
];

export function zoneColor(index: number) {
  return ZONE_COLORS[index % ZONE_COLORS.length];
}

/** Capa transparente sobre el video para dibujar las zonas de inspección. */
export function ZoneEditor({ zones, onAdd, locked, children }: Props) {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [origin, setOrigin] = useState<{ x: number; y: number } | null>(null);
  const [draft, setDraft] = useState<Rect | null>(null);

  const relative = (e: React.PointerEvent) => {
    const rect = boxRef.current!.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height)),
    };
  };

  const rectFrom = (a: { x: number; y: number }, b: { x: number; y: number }): Rect => ({
    x: Math.min(a.x, b.x),
    y: Math.min(a.y, b.y),
    w: Math.abs(a.x - b.x),
    h: Math.abs(a.y - b.y),
  });

  return (
    <div
      ref={boxRef}
      className="relative touch-none select-none overflow-hidden rounded-xl bg-black"
      onPointerDown={(e) => {
        if (locked) return;
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
        const p = relative(e);
        setOrigin(p);
        setDraft({ x: p.x, y: p.y, w: 0, h: 0 });
      }}
      onPointerMove={(e) => {
        if (!origin) return;
        setDraft(rectFrom(origin, relative(e)));
      }}
      onPointerUp={(e) => {
        if (!origin) return;
        const next = rectFrom(origin, relative(e));
        setOrigin(null);
        setDraft(null);
        // Un clic suelto no hace nada: las zonas se borran desde la lista,
        // nunca por tocar el video sin querer.
        if (next.w > 0.02 && next.h > 0.02) onAdd(next);
      }}
    >
      {children}

      {zones.map((zone, i) => (
        <div
          key={zone.name}
          className="pointer-events-none absolute border-2"
          style={{
            left: `${zone.x * 100}%`,
            top: `${zone.y * 100}%`,
            width: `${zone.w * 100}%`,
            height: `${zone.h * 100}%`,
            borderColor: zoneColor(i),
          }}
        >
          <span
            className="absolute left-0 top-0 -translate-y-full px-1 text-[10px] font-bold"
            style={{ color: zoneColor(i) }}
          >
            {zone.name}
          </span>
        </div>
      ))}

      {draft && (
        <div
          className="pointer-events-none absolute border-2 border-dashed border-white"
          style={{
            left: `${draft.x * 100}%`,
            top: `${draft.y * 100}%`,
            width: `${draft.w * 100}%`,
            height: `${draft.h * 100}%`,
          }}
        />
      )}

      {zones.length === 0 && !locked && (
        <div className="pointer-events-none absolute inset-x-0 bottom-3 text-center text-sm text-white/90">
          Arrastrá para delimitar una zona de inspección
        </div>
      )}
    </div>
  );
}
