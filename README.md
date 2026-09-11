# EdgeQA

Estación de inspección visual que aprende "qué es normal" con 8 a 15 fotos de
piezas correctas, sin etiquetar defectos ni entrenar modelos. Corre entera en
local: Next.js toma la cámara del navegador y FastAPI resuelve la anomalía con
DINOv2.

Contexto completo del proyecto en `openspec/changes/edgeqa-demo/`:
`proposal.md` (qué y por qué), `design.md` (decisiones técnicas) y
`tasks.md` (estado del trabajo).

## Requisitos

- Python 3.11
- Node 20 o superior
- Una webcam

## Puesta en marcha

Dos terminales, una por servicio.

### Backend — puerto 8000

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

La primera ejecución descarga DINOv2-S de HuggingFace (unos 90 MB) y tarda.
Las siguientes arrancan con el modelo ya cacheado.

Para comprobar que responde: `curl http://localhost:8000/health`

### Frontend — puerto 3000

```bash
cd frontend
npm install
npm run dev
```

Abrir http://localhost:3000 y dar permiso de cámara al navegador.

## Cómo se usa

1. **Delimitar el área.** Arrastrar un rectángulo sobre el video, ajustado a la
   pieza. No debe entrar mesa, sombra ni ningún objeto ajeno: todo lo que quede
   dentro se aprende como normal.
2. **Capturar de 10 a 12 piezas correctas.** Levantar y reapoyar la pieza entre
   capturas, con desvíos de milímetros y sin cambiar la orientación.
3. **Revisar las miniaturas** y descartar con un clic cualquier toma mal
   encuadrada.
4. **Enrolar.** El sistema construye el banco y calibra el umbral solo.
5. **Inspeccionar.** Cada pieza devuelve veredicto, score y mapa de calor.

Una vez enrolado, la cámara no se mueve. Si se corre, hay que enrolar de nuevo.

## Estado local

El banco de memoria vive en `backend/storage/bank.pkl` y está fuera de git: es
específico de cada cámara y cada setup físico. Al clonar el proyecto en otra
máquina hay que enrolar desde cero.

Para descartar el enrolamiento actual: botón **Reiniciar**, o
`curl -X POST http://localhost:8000/reset`.

## API

| Método | Ruta | Qué hace |
|--------|------|----------|
| GET | `/health` | Estado del modelo y del banco |
| POST | `/enroll` | Construye el banco con 8 a 15 capturas |
| POST | `/infer` | Evalúa una pieza: veredicto, score y heatmap |
| GET/PUT | `/config` | Lee y ajusta la sensibilidad |
| POST | `/reset` | Descarta el enrolamiento |
