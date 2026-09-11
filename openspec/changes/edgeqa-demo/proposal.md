# EdgeQA — Demo de inspección visual few-shot

## Por qué

La inspección visual en planta depende de operarios que se fatigan, y las
soluciones de visión tradicionales necesitan miles de imágenes de defectos
que la fábrica todavía no tiene. Queremos demostrar que con un puñado de
fotos de piezas correctas alcanza para levantar una estación de inspección
funcional.

Este cambio construye esa demo end-to-end en una jornada de hackathon.

## Qué construimos

Una estación de inspección de una sola cámara, corriendo enteramente en
local, que permite:

1. **Configurar** la estación delimitando el área de inspección (ROI) sobre
   el video en vivo de la webcam.
2. **Enrolar** la pieza de referencia capturando en vivo entre 8 y 15
   ejemplares correctos, recolocando la pieza entre capturas y revisando
   las miniaturas antes de confirmar.
3. **Inspeccionar** una pieza nueva y obtener un veredicto APROBADO/RECHAZADO
   en menos de un segundo, acompañado de un mapa de calor que señala la
   región anómala.
4. **Ajustar la sensibilidad** con un control deslizante, viendo en vivo cómo
   cambia el veredicto sobre la última pieza inspeccionada.

Todo el material de referencia se captura en vivo: no hay archivos
preparados de antemano, lo que permite cambiar de producto en un minuto.

El caso de prueba son saquitos de té La Virginia con siete defectos
preparados a mano, desde una esquina arrancada hasta un trazo de lapicera
que altera una letra del logo.

## Criterios de éxito

**Comprometido:** detectar los cinco defectos de escala media o superior
(arrugado, dos esquinas rotas, dos letras rellenas) sin rechazar piezas
sanas recolocadas.

**Ambicioso:** detectar además los dos defectos tipográficos del logo,
que miden menos de un milímetro cuadrado de superficie alterada.

La demo se considera exitosa alcanzando el nivel comprometido.

## Fuera de alcance

- Múltiples cámaras o múltiples productos simultáneos
- Autenticación, usuarios, roles
- Base de datos, historial persistente, reportes
- Facturación, licenciamiento, suscripciones
- Despliegue, contenedores, CI
- Tests automatizados
- Cualquier ejecución en la nube
