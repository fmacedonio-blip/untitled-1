# Resultados del gate — Bloque 1

Medición realizada el 11 de septiembre de 2026 sobre el setup definitivo:
webcam encastrada en caja, saquito apoyado contra el borde interno,
iluminación de ambiente controlada por la propia caja.

## Condiciones

| Parámetro | Valor |
|-----------|-------|
| Muestras de enrolamiento | 15 |
| Parches en el banco | 20.535 (15 x 1369) |
| ROI | 0.33, 0.06 — 0.47 x 0.89 |
| Resolución de captura | 1280x720 |
| Dispositivo | MPS (Apple Silicon) |
| Umbral base (leave-one-out) | 0.2001 |
| Latencia de inferencia | 287–371 ms |

## Piezas correctas

| Muestra | Score | Ratio con sensibilidad 1.0 |
|---------|-------|---------------------------|
| sana A | 0.1457 | 0.73x |
| sana B | 0.1254 | 0.63x |
| sana C | 0.1286 | 0.64x |

Rango observado sobre el total de la sesión: **0.094 – 0.146**.

## Piezas defectuosas

Ordenadas por score descendente. El ratio se calcula contra el umbral
resultante de sensibilidad 1.0, es decir 0.2001.

| # | Defecto | Superficie | Score | Ratio | Veredicto |
|---|---------|-----------|-------|-------|-----------|
| 7 | "DURAZNO": letra O rellena | ~0.3% | 0.3952 | 1.98x | RECHAZADO |
| 5 | Esquina inferior arrancada | ~3% | 0.3850 | 1.92x | RECHAZADO |
| 2 | Saquito arrugado por completo | ~40% | 0.3549 | 1.77x | RECHAZADO |
| 3 | Esquina superior arrancada | ~3% | 0.3173 | 1.59x | RECHAZADO |
| 4 | "saquito": letra o rellena | ~0.05% | 0.1309 | 0.65x | aprobado |
| 1 | Logo: la L de "La" alterada | ~0.05% | 0.1149 | 0.57x | aprobado |
| 6 | Logo: la a final con cola | ~0.03% | 0.0939 | 0.47x | aprobado |

## Lectura

Los cuatro defectos de escala media o superior separan con un margen
amplio: el más bajo de ellos mide 0.3173 contra 0.1457 de la peor pieza
sana, un factor de 2,2. Entre 0.15 y 0.32 no cae ninguna medición, de
modo que el umbral admite un rango generoso sin comprometer el resultado.

Los tres defectos tipográficos, en cambio, no se separan: miden entre
0.094 y 0.131, dentro del rango de las piezas correctas. El caso extremo
es el defecto 6, cuyo score es **inferior al de cualquier pieza sana
medida**. No es un problema de calibración: a 518px cada parche cubre
unos 17px reales y la alteración ocupa una fracción de parche, sobre una
tipografía que ya era negra y curva. La señal se pierde dentro del propio
parche antes de llegar a la comparación con el banco.

Bajar el umbral no los recupera: para capturar un score de 0.0939 habría
que fijar el corte por debajo de la totalidad de las piezas correctas.

## Calibración adoptada

El umbral base de 0.2001 quedó por encima de las piezas sanas reales
(0.094–0.146) porque el leave-one-out toma el máximo y al menos una de
las 15 capturas de enrolamiento quedó desalineada respecto del resto.

Con **sensibilidad 1.00** el umbral efectivo es 0.2001, ubicado dentro
del hueco entre ambos grupos: las piezas correctas quedan un 27% por
debajo y los defectos detectables un 59% por encima.

## Veredicto del gate

**Criterio comprometido: alcanzado.** Los defectos de escala media o
superior se detectan sin rechazar piezas sanas recolocadas.

**Criterio ambicioso: no alcanzado.** Los defectos tipográficos requieren
más resolución efectiva, no un umbral distinto. Corresponde evaluar la
tarea 1.11 (tiling 2x2) o un ROI acotado a la zona del logo.
