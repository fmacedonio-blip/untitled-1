# Inspección visual few-shot

## ADDED Requirements

### Requirement: Definición del área de inspección
El sistema SHALL permitir al operario delimitar un área rectangular de
interés sobre el video en vivo de la cámara, y SHALL aplicar ese mismo
recorte tanto al enrolar como al inspeccionar.

#### Scenario: El operario delimita el área
- **GIVEN** el video de la cámara está visible en pantalla
- **WHEN** el operario arrastra un rectángulo sobre la pieza
- **THEN** el área queda registrada y se muestra resaltada sobre el video

#### Scenario: El área persiste entre operaciones
- **GIVEN** existe un área de inspección definida
- **WHEN** el operario enrola piezas o inspecciona una pieza nueva
- **THEN** ambas operaciones usan exactamente el mismo recorte

### Requirement: Enrolamiento de la pieza de referencia
El sistema SHALL construir un banco de memoria a partir de entre 8 y 15
capturas de piezas correctas tomadas en vivo desde la cámara, sin requerir
etiquetado, entrenamiento ni preparación previa de archivos.

#### Scenario: Enrolamiento exitoso
- **GIVEN** el operario capturó al menos 8 piezas correctas
- **WHEN** confirma el enrolamiento
- **THEN** el sistema construye el banco y queda listo para inspeccionar
- **AND** el banco se guarda en disco

#### Scenario: Muestras insuficientes
- **GIVEN** el operario capturó menos de 8 piezas
- **WHEN** intenta confirmar el enrolamiento
- **THEN** el sistema lo rechaza indicando cuántas capturas faltan

#### Scenario: El banco sobrevive un reinicio
- **GIVEN** existe un banco enrolado y guardado en disco
- **WHEN** el backend se reinicia
- **THEN** el banco se recarga automáticamente sin volver a enrolar

### Requirement: Control de calidad del enrolamiento
El sistema SHALL mostrar las capturas de enrolamiento como miniaturas y
SHALL permitir descartar cualquiera de ellas antes de construir el banco,
para que el operario detecte tomas mal alineadas.

#### Scenario: El operario revisa sus capturas
- **GIVEN** el operario capturó varias piezas correctas
- **WHEN** mira la pantalla de enrolamiento
- **THEN** ve una miniatura de cada captura tomada hasta el momento

#### Scenario: Descarte de una captura desalineada
- **GIVEN** una captura quedó mal encuadrada respecto de las demás
- **WHEN** el operario la descarta
- **THEN** deja de contar para el banco y el contador se actualiza

### Requirement: Veredicto de inspección
El sistema SHALL emitir un veredicto binario APROBADO o RECHAZADO sobre
una pieza, en menos de un segundo, comparando sus parches contra el banco.

#### Scenario: Pieza correcta
- **GIVEN** un banco enrolado y una pieza sin defectos
- **WHEN** el operario inspecciona la pieza
- **THEN** el sistema responde APROBADO en menos de un segundo

#### Scenario: Pieza defectuosa
- **GIVEN** un banco enrolado y una pieza con un defecto visible
- **WHEN** el operario inspecciona la pieza
- **THEN** el sistema responde RECHAZADO en menos de un segundo

#### Scenario: Inspección sin enrolamiento previo
- **GIVEN** no existe ningún banco enrolado
- **WHEN** el operario intenta inspeccionar
- **THEN** el sistema lo indica y ofrece iniciar el enrolamiento

### Requirement: Localización del defecto
El sistema SHALL acompañar cada veredicto con un mapa de calor superpuesto
sobre la pieza, señalando las regiones que más se apartan de lo normal.

#### Scenario: El defecto queda señalado
- **GIVEN** una pieza rechazada por un defecto localizado
- **WHEN** se muestra el resultado
- **THEN** el mapa de calor marca la región donde está el defecto

### Requirement: Ajuste de sensibilidad
El sistema SHALL calcular un umbral inicial a partir de las muestras de
enrolamiento, y SHALL permitir al operario ajustarlo con un control
deslizante viendo el efecto sobre la última pieza inspeccionada.

#### Scenario: Umbral inicial automático
- **GIVEN** el operario completó el enrolamiento
- **WHEN** el banco queda construido
- **THEN** el sistema fija un umbral sin intervención del operario

#### Scenario: Reevaluación en vivo
- **GIVEN** una pieza recién inspeccionada en pantalla
- **WHEN** el operario mueve el control de sensibilidad
- **THEN** el veredicto se recalcula sin volver a capturar la pieza

### Requirement: Visibilidad operativa
La interfaz SHALL presentar el veredicto con indicadores de alto contraste
legibles a distancia, y SHALL llevar la cuenta de piezas aprobadas y
rechazadas durante la sesión.

#### Scenario: Veredicto legible a distancia
- **WHEN** el sistema emite un veredicto
- **THEN** la pantalla lo muestra ocupando una porción dominante del área
  visible, con color de alto contraste según el resultado

#### Scenario: Conteo de sesión
- **GIVEN** varias piezas inspeccionadas
- **WHEN** el operario mira el panel
- **THEN** ve cuántas fueron aprobadas y cuántas rechazadas
