"use client";

import { useRef, useState } from "react";
import type { Roi } from "@/lib/api";

type Props = {
  roi: Roi | null;
  onChange: (roi: Roi | null) => void;
  children: React.ReactNode;
};

/** Capa transparente sobre el video para dibujar el área de inspección. */
export function RoiSelector({ roi, onChange, children }: Props) {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [origin, setOrigin] = useState<{ x: number; y: number } | null>(null);
  const [draft, setDraft] = useState<Roi | null>(null);

  const relative = (e: React.PointerEvent) => {
    const rect = boxRef.current!.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height)),
    };
  };

  const rectFrom = (a: { x: number; y: number }, b: { x: number; y: number }): Roi => ({
    x: Math.min(a.x, b.x),
    y: Math.min(a.y, b.y),
    w: Math.abs(a.x - b.x),
    h: Math.abs(a.y - b.y),
  });

  const shown = draft ?? roi;

  return (
    <div
      ref={boxRef}
      className="relative touch-none select-none overflow-hidden rounded-xl bg-black"
      onPointerDown={(e) => {
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
        // Un clic suelto limpia la selección; un arrastre real la define.
        onChange(next.w > 0.04 && next.h > 0.04 ? next : null);
      }}
    >
      {children}

      {shown && (
        <>
          <div className="pointer-events-none absolute inset-0 bg-black/45" />
          <div
            className="pointer-events-none absolute border-2 border-sky-400 shadow-[0_0_0_9999px_rgba(0,0,0,0.45)]"
            style={{
              left: `${shown.x * 100}%`,
              top: `${shown.y * 100}%`,
              width: `${shown.w * 100}%`,
              height: `${shown.h * 100}%`,
              boxShadow: "0 0 0 9999px rgba(0,0,0,0.45)",
              background: "transparent",
            }}
          />
        </>
      )}

      {!shown && (
        <div className="pointer-events-none absolute inset-x-0 bottom-3 text-center text-sm text-white/90">
          Arrastrá para delimitar el área de inspección
        </div>
      )}
    </div>
  );
}
