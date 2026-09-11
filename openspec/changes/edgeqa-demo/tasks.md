# Tareas

Ordenadas por riesgo. Todo el enrolamiento ocurre en vivo desde la cámara:
no hay dataset en disco ni preparación previa de imágenes.

## Bloque 1 — Backend y captura mínima

Objetivo: llegar lo antes posible a poder enrolar y medir de verdad.
La interfaz de este bloque es deliberadamente fea; es el esqueleto sobre
el que crece la interfaz final, no un descarte.

- [x] 1.1 Entorno Python: torch, transformers, pillow, numpy, fastapi
- [x] 1.2 Cargar DINOv2-S y extraer la grilla de parches a 518px,
      confirmando la forma del tensor
- [x] 1.3 FastAPI con CORS hacia localhost:3000
- [x] 1.4 `POST /enroll`: recibe capturas en base64, recorta por ROI,
      construye el banco de memoria
- [x] 1.5 Calibración del umbral por leave-one-out sobre el enrolamiento
- [x] 1.6 `POST /infer`: devuelve score y veredicto
- [x] 1.7 Proyecto Next.js con video en vivo por getUserMedia, fijando
      la resolución de captura explícitamente
- [x] 1.8 Selector de ROI arrastrando sobre el video
- [x] 1.9 Página cruda: botón capturar, botón enrolar, botón inspeccionar,
      y el score impreso como número sin formato

**GATE: enrolar 12 piezas correctas en vivo y pasar las 7 defectuosas.
Si los scores no separan, no se avanza a la interfaz definitiva. Se sube
resolución o se activa el plan B de tiling 2x2.**

- [ ] 1.10 Registrar qué defectos se detectan y con qué margen
- [ ] 1.11 Si los defectos del logo no separan: probar tiling 2x2

## Bloque 2 — Interfaz operativa

- [ ] 2.1 Tailwind y estructura visual de la pantalla
- [ ] 2.2 Pantalla de enrolamiento con tira de miniaturas de las capturas
- [ ] 2.3 Permitir descartar una captura individual de la tira
- [ ] 2.4 Indicaciones en pantalla sobre cómo recolocar la pieza
- [ ] 2.5 Veredicto a pantalla casi completa, verde o rojo
- [ ] 2.6 Heatmap superpuesto sobre la pieza inspeccionada
- [ ] 2.7 `GET/PUT /config` y slider de sensibilidad que reevalúa sin
      volver a capturar
- [ ] 2.8 Contadores de aprobadas y rechazadas

## Bloque 3 — Robustez y cierre

- [ ] 3.1 Persistencia del banco a disco y recarga al arrancar
- [ ] 3.2 Ensayo completo: configurar, enrolar y pasar las 7 defectuosas
      más varias piezas correctas
- [ ] 3.3 Ajustar la sensibilidad al punto que mejor funcione en vivo
- [ ] 3.4 Escribir el guion de la demo, de defecto obvio a defecto sutil

## Si sobra tiempo

- [ ] 4.1 Enrolar un objeto cualquiera de la sala en vivo, como remate
      de la demo
- [ ] 4.2 Disparo automático al detectar escena estable
- [ ] 4.3 Tira de miniaturas con las últimas piezas rechazadas
