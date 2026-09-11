"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Resolución pedida explícitamente: garantiza que todas las capturas de la
// sesión tengan el mismo tamaño, sin depender de cómo esté la ventana.
const CAPTURE_WIDTH = 1280;
const CAPTURE_HEIGHT = 720;

export function useCamera() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resolution, setResolution] = useState<string>("");

  useEffect(() => {
    let stream: MediaStream | null = null;

    async function start() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: CAPTURE_WIDTH },
            height: { ideal: CAPTURE_HEIGHT },
          },
          audio: false,
        });
        if (!videoRef.current) return;
        videoRef.current.srcObject = stream;
        await videoRef.current.play();

        const track = stream.getVideoTracks()[0];
        const settings = track.getSettings();
        setResolution(`${settings.width}x${settings.height}`);
        setReady(true);
        setError(null);
      } catch (err) {
        // En desarrollo React monta dos veces y el segundo montaje aborta el
        // play() del primero. Ese caso no es un fallo: el stream termina
        // abriendo bien, así que no lo reportamos como error.
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(
          err instanceof Error
            ? `No se pudo abrir la cámara: ${err.message}`
            : "No se pudo abrir la cámara",
        );
      }
    }

    start();
    return () => stream?.getTracks().forEach((t) => t.stop());
  }, []);

  /** Captura el cuadro actual como data URL JPEG. */
  const capture = useCallback((): string | null => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return null;

    const canvas = canvasRef.current ?? document.createElement("canvas");
    canvasRef.current = canvas;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.92);
  }, []);

  return { videoRef, capture, ready, error, resolution };
}
