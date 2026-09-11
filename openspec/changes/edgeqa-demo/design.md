# Diseño técnico — EdgeQA demo

## Catálogo de defectos del caso de prueba

Siete piezas defectuosas preparadas a mano, ordenadas por superficie
alterada. El orden importa: define qué es razonable esperar y en qué
secuencia conviene mostrar la demo, de lo evidente a lo sutil.

| # | Defecto | Superficie alterada | Dificultad |
|---|---------|--------------------|-----------|
| 2 | Saquito arrugado por completo | ~40% | Trivial |
| 3 | Esquina superior arrancada | ~3% | Fácil |
| 5 | Esquina inferior arrancada | ~3% | Fácil |
| 7 | "DURAZNO": letra O rellena con negro | ~0.3% | Media |
| 4 | "saquito": letra o rellena, texto chico | ~0.05% | Media |
| 1 | Logo: la L de "La" alterada con lapicera | ~0.05% | Difícil |
| 6 | Logo: la a final con una cola agregada | ~0.03% | Difícil |

Los dos últimos son cualitativamente distintos: no agregan un elemento
nuevo sobre fondo liso, sino que modifican una tipografía que ya es negra
y curva. El parche que los contiene ya era visualmente complejo antes del
defecto, así que la señal se confunde con la varianza natural de
recolocación de la pieza.

## Decisión: embeddings por parche, no vector global

El enfoque ingenuo —un vector por imagen y distancia al centroide— falla
en este caso. Un disco negro de 55px sobre una pieza de 650px mueve el
descriptor global apenas, y queda por debajo del ruido de posicionamiento.

Adoptamos en cambio un esquema estilo PatchCore simplificado:

```
imagen -> crop ROI -> resize 518x518 -> DINOv2-S/14
                                            |
                                    grilla 37x37 parches
                                    (1369 vectores de 384 dims)
```

Durante el enrolamiento, todos los parches de todas las piezas correctas
se acumulan en un banco de memoria. Con 10 piezas son ~13.700 vectores,
un volumen que se recorre por fuerza bruta sin necesidad de indexado
aproximado ni coreset subsampling.

Durante la inferencia, cada parche de la pieza nueva se compara contra el
banco y se queda con la distancia a su vecino más cercano. El resultado
es un mapa de anomalía de 37x37, que se escala bilinealmente al tamaño de
la imagen para superponerlo como mapa de calor.

**Por qué esto y no un autoencoder o un clasificador:** ambos requieren
entrenamiento, y el entrenamiento requiere tiempo y datos de defectos.
El valor de la propuesta es precisamente no necesitar ninguno de los dos.

## Decisión: resolución 518, no 224

DINOv2 acepta entradas mayores a 224 interpolando los embeddings
posicionales. A 518px cada parche cubre unos 17px reales de la pieza:

- El disco negro del defecto 7 ocupa unos 3 parches completos.
- El punto del defecto 4 ocupa aproximadamente 1 parche.
- Los trazos del logo (1 y 6) ocupan una fracción de parche.

A 224px, en cambio, cada parche cubriría ~40px reales y hasta el defecto 7
quedaría diluido. El costo es latencia: ~200ms contra ~40ms en CPU.

**Priorizamos detección sobre latencia.** Una demo que detecta el defecto
sutil en 300ms convence; una que responde en 40ms sin verlo, no.

**Plan B si los defectos del logo no se separan:** dividir el ROI en una
grilla de 2x2 y procesar cada porción a 448px por separado, cuadruplicando
la resolución efectiva a costa de ~4x la latencia. Se implementa como una
opción de configuración, no como un rediseño.

## Decisión: score por media del top-k, no máximo

El máximo de las distancias es la formulación clásica, pero es frágil: un
único parche ruidoso en el borde de la pieza dispara un falso positivo.

Usamos el promedio de los k parches con mayor distancia (k=5). Mantiene la
sensibilidad a defectos locales —cinco parches contiguos siguen siendo una
región muy pequeña— y amortigua los valores atípicos aislados.

## Decisión: región de interés obligatoria

El campo de visión de la cámara contiene elementos ajenos a la pieza: la
línea donde se unen dos superficies del fondo, partículas de polvo sobre
la mesa, y la sombra que proyecta la propia pieza.

Con un banco construido sobre pocas muestras, todo eso se incorpora como
"normal", y cualquier variación posterior —una mota que se corre, una
sombra que cambia, una mano que entra en cuadro— se convierte en falso
positivo.

El ROI se define una sola vez al configurar la estación, dibujando un
rectángulo sobre el video en vivo, y se aplica idéntico en enrolamiento e
inferencia. Es además lo que haría una estación industrial real.

## Decisión: captura en el navegador

La webcam se accede con `getUserMedia` desde el frontend y los cuadros se
envían al backend como JPEG en base64.

La alternativa —abrir la cámara con OpenCV desde Python— es una fuente
conocida de fricción en macOS: permisos de TCC, conflictos con otras
aplicaciones que tomaron el dispositivo, y demoras de inicialización. En
una jornada de trabajo no hay margen para pelear con eso.

## Decisión: umbral calibrado por leave-one-out

Con solo muestras correctas no hay forma directa de fijar el umbral. Lo
derivamos así:

```
para cada muestra i del set de enrolamiento:
    score_i = inferir(muestra_i) contra el banco formado
              por todas las demás muestras
umbral = max(score_i) * factor_sensibilidad
```

Esto da un piso honesto: el umbral queda justo por encima de la peor
pieza que sabemos que es correcta. El factor de sensibilidad arranca en
1.15 y el operario lo ajusta con un control deslizante entre 1.0 y 2.0.

El control tiene además valor narrativo en la demo: permite mostrar en
vivo cómo se endurece o afloja el criterio sobre una misma pieza.

## Decisión: enrolamiento en vivo, sin dataset en disco

La primera aproximación fue preparar carpetas de imágenes y validar el
algoritmo con un script. Se descartó por tres motivos.

El primero es práctico: capturar con una aplicación de escritorio produjo
tres resoluciones distintas para la misma cámara, porque la herramienta
recorta según el tamaño de su ventana. Pidiendo la resolución
explícitamente por `getUserMedia`, ese problema desaparece.

El segundo es que el enrolamiento en vivo **es** la propuesta de valor.
Configurar una estación en un minuto mostrando piezas correctas es
exactamente lo que se promete; hacerlo en pantalla lo demuestra, mientras
que un dataset preparado de antemano obliga a explicarlo con palabras.

El tercero es de iteración: cambiar de producto, recuperarse de un
movimiento accidental de la cámara o reajustar el umbral pasa a costar un
minuto en lugar de una sesión de fotos.

El gate de validación no se elimina, se adelanta: el primer bloque de
trabajo termina en una página cruda que solo imprime el score, y recién
cuando los números separan piezas correctas de defectuosas se construye la
interfaz definitiva.

## Riesgo principal: varianza de enrolamiento mal calibrada

El banco de memoria tolera exactamente aquello que se le mostró durante el
enrolamiento. Ese margen tiene dos formas de salir mal, y las dos son
silenciosas.

**Varianza insuficiente.** Si todas las capturas son idénticas, cualquier
recolocación en la inspección dispara un rechazo. La demo falla al
colocar una pieza perfectamente sana.

**Varianza excesiva.** Si las capturas incluyen rotaciones amplias,
desplazamientos grandes o piezas parcialmente fuera de cuadro, el banco
aprende que "la pieza en cualquier orientación es normal". El umbral
resultante se dispara y los defectos pequeños quedan sepultados bajo el
ruido de posicionamiento. No se detecta nada.

Este segundo caso se observó en la práctica durante la preparación: un set
de piezas correctas fotografiadas con rotaciones de hasta noventa grados,
contra piezas defectuosas todas verticales y centradas. Cualquier medición
sobre ese material habría sido inservible.

**Criterio correcto:** la pieza siempre en la misma orientación, con
desvíos de pocos milímetros y a lo sumo dos o tres grados de inclinación.
La variación que se introduce a propósito durante el enrolamiento es
exactamente la que el sistema va a tolerar después, ni más ni menos.

**Mitigación en la interfaz:** la pantalla de enrolamiento muestra una
tira con las miniaturas de todas las capturas. Una toma desalineada se
distingue de un vistazo entre las demás y puede descartarse antes de
construir el banco.

## Arquitectura

```
┌────────────────────────────┐         ┌──────────────────────────┐
│  Next.js  :3000            │  HTTP   │  FastAPI  :8000          │
│                            │ ──────▶ │                          │
│  getUserMedia -> <video>   │  JPEG   │  POST /enroll            │
│  selector de ROI           │  base64 │  POST /infer             │
│  semáforo APROBADO/RECHAZ. │         │  GET/PUT /config         │
│  heatmap en <canvas>       │ ◀────── │                          │
│  slider de sensibilidad    │  score  │  DINOv2-S en memoria     │
│  contadores OK/NOK         │ +heatmap│  banco de parches (RAM)  │
└────────────────────────────┘         │  pickle a disco          │
                                       └──────────────────────────┘
```

El banco se persiste a disco tras cada enrolamiento. Reiniciar el backend
durante la demo no debe costar una recalibración.
