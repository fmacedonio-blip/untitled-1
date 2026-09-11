## Resumen Ejecutivo & Propuesta de Valor

**Nombre Sugerido:** EdgeQA (o VisionZero).

**El Concepto:** Un sistema de Control de Calidad Visual (Visual QA) industrial Plug & Play que elimina el problema del "arranque en frío" en la detección de defectos.

**La Propuesta:** Permitir a cualquier operario de planta configurar una estación de inspección automatizada en menos de un minuto mostrando solo un puñado de ejemplos físicos de una pieza "perfecta", sin necesidad de etiquetar datos ni entrenar modelos.

## El Problema: El "Cold-Start" Industrial

Las fábricas medianas y PyMEs dependen de la inspección visual humana, la cual es altamente propensa a la fatiga y a dejar pasar defectos costosos.

Las soluciones tradicionales de visión artificial son prohibitivas: exigen integraciones costosas y la recolección de miles de imágenes de anomalías raras (que la fábrica aún no tiene) para entrenar una red neuronal desde cero.

El entorno industrial exige soluciones con privacidad absoluta y latencia acotada, lo que invalida depender de APIs lentas en la nube.

## La Solución Técnica: Few-Shot Anomaly Detection

**Extracción de Embeddings Locales:** Utilizamos un modelo fundacional (DINOv2) para procesar la imagen. En lugar de resumir la pieza en un único vector, conservamos la **grilla completa de embeddings por parche** —cientos de vectores, cada uno describiendo una región pequeña de la pieza— porque un defecto de pocos milímetros se diluye por completo en un descriptor global.

**Definición de Normalidad:** Al pasar entre 8 y 15 piezas correctas por el modelo, el sistema construye instantáneamente un **banco de memoria** con todos los parches considerados normales. No hace falta etiquetar nada: basta con mostrar lo que está bien.

**Inferencia Inmediata:** Al colocar una nueva pieza, se extraen sus parches y se mide, para cada uno, la distancia al parche normal más parecido del banco. Si las regiones más atípicas superan el umbral de tolerancia, la pieza se marca como anomalía. El sistema además devuelve un **mapa de calor que señala exactamente dónde** está el defecto, lo que convierte al veredicto en algo auditable por el operario en lugar de una caja negra.

**Rendimiento:** Inferencia sub-segundo sobre CPU en hardware de escritorio, con margen para bajar a decenas de milisegundos al desplegar sobre GPU o acelerador embebido.

## Modelo de Negocio & Arquitectura

**Despliegue Local (Edge AI):** Todo el cómputo y la inferencia del modelo se realizan de forma 100% local en la planta, garantizando autonomía total sin necesidad de internet.

**Interfaz Operativa:** Un panel de control web ultrarrápido y responsivo construido en Next.js con Tailwind CSS, diseñado con botones gigantes e indicadores de alto contraste (Aprobado/Rechazado) para que el operario lo use fácilmente en la línea de montaje. El mapa de calor se superpone sobre la pieza para justificar cada rechazo.

**Monetización:** Licencia de software B2B cobrada mediante una suscripción mensual por cada "puesto o cámara de inspección" activa, donde el retorno de inversión para el cliente se paga solo al evitar la devolución de un único lote defectuoso.
