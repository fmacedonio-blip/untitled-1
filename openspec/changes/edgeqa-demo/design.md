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

## Decisión: zonas de inspección múltiples

El gate mostró que los defectos tipográficos no se separan (ver
`resultados-gate.md`): miden entre 0.094 y 0.131, dentro del rango de las
piezas correctas. El más sutil puntúa por debajo de cualquier pieza sana
medida.

La causa es geométrica, no de capacidad del modelo. Con un ROI que abarca
la pieza entera, unos 650px reales se redimensionan a 518 y cada parche
cubre ~17px. El trazo agregado a una letra ocupa menos de un parche, y ahí
se promedia con la tipografía negra que ya estaba en esa región. Un modelo
mayor recibiría el mismo parche ya degradado: la información se pierde en
el resampleo, antes de la inferencia.

Sustituimos entonces el ROI único por una lista de **zonas**, cada una con
su propio rectángulo, su banco y su umbral:

```
                         ┌──────────────────┐
   una captura ──┬──────▶│ zona "pieza"     │─┐
                 ├──────▶│ zona "logo"      │─┤
                 ├──────▶│ zona "sabor"     │─┼─▶ RECHAZADO si
                 └──────▶│ zona "texto"     │─┘   alguna supera
                         └──────────────────┘     su propio umbral
```

Cada zona se recorta de la misma captura y se escala a 518px por separado.
Una zona de 160px de ancho pasa a tener parches de ~4px reales: cuatro
veces la resolución efectiva sobre lo que importa.

**Por qué no basta con subir la resolución global.** Llevar la pieza
entera a 1036px cuadruplicaría el costo sobre toda la superficie para
ganar detalle en las regiones que no lo necesitan, y DINOv2 degrada al
interpolar los embeddings posicionales muy lejos de su tamaño de
entrenamiento. Recortar primero y escalar después concentra el presupuesto
de píxeles donde hace falta.

**Por qué un umbral por zona y no uno global.** El score es el promedio
del top-k de las distancias. Con una sola zona, un defecto diminuto
compite contra la varianza de los 1369 parches de toda la pieza,
incluida la del plástico que se arruga distinto en cada colocación.
Calibrando cada zona por separado, el logo se compara solo contra logos y
su tolerancia no queda contaminada por el resto.

**Veredicto agregado.** La pieza se rechaza si cualquier zona supera su
umbral. La respuesta indica además qué zona falló, lo que convierte el
veredicto en algo accionable: no "esta pieza está mal" sino "el logo está
mal".

**Costo.** La latencia crece de forma aproximadamente lineal con el número
de zonas: cuatro zonas rondan 1,2s contra los ~300ms actuales. Se acepta
el intercambio; la detección importa más que la latencia en esta demo, y
la operación sigue siendo un solo clic para el operario.

**Compatibilidad.** Una sola zona que cubra la pieza entera reproduce
exactamente el comportamiento anterior, de modo que el esquema previo es
un caso particular del nuevo.

## Intentos descartados para el ruido de recolocación

Dos hipótesis sobre por qué los defectos tipográficos no separan de las
piezas sanas, ambas medidas sobre las capturas reales de enrolamiento y
ambas descartadas.

**Tolerancia espacial en la búsqueda del vecino.** La idea era restringir
la comparación de cada parche a un entorno de la grilla, de modo que un
desplazamiento de la pieza encontrara su correspondencia unas posiciones
más allá en lugar de contar como anomalía. Medido con radios de 2 y 3
parches contra la búsqueda global, la dispersión del enrolamiento no se
movió: 1,26x contra 1,27x en la zona del producto, 1,61x contra 1,75x en
la del logo. Los scores absolutos subieron, porque restringir el entorno
sólo quita candidatos. La implementación quedó en el código detrás de
`SEARCH_RADIUS = 0`, que es la búsqueda global.

**Tamaño del top-k.** Si el score promedia los cinco peores parches, un
defecto de un parche queda diluido entre cuatro valores de ruido; bajar k
a 1 debería favorecerlo. La medición muestra lo contrario: en la zona del
logo la dispersión se mantiene alrededor de 1,7x para k entre 1 y 10. El
ruido no proviene de parches aislados sino de la región completa.

Lo que ambas mediciones dicen es que la varianza no está en cómo se
agregan las distancias ni en dónde se busca el vecino, sino en que la
pieza se ve genuinamente distinta entre capturas: el plástico se arruga,
la luz incide diferente y la tipografía se deforma con la superficie. Esa
varianza es del mismo orden que un trazo de menos de un milímetro
cuadrado, y ninguna métrica sobre los mismos embeddings la separa.
