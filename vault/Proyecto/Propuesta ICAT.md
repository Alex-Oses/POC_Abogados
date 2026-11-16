# Propuesta ICAT

Fuente: *Propuesta para el ICAT · Software de transcripción de documentos escaneados* (06/11/2026).

## En una frase

Herramienta local, en catalán y castellano, que lee la documentación escaneada que ya recibe el Colegio, empezando por justicia gratuita, y deja revisar y validar cada página junto a su imagen, con la imagen gráfica del ICAT.

## Contexto del ICAT

- Dos públicos: colegiados (área privada, turno de oficio, formación) y ciudadanía (justicia gratuita, orientación, quejas).
- Herramientas actuales: **UNITRAM** (trámites y cita previa), extranet de colegiados, certificado **ACA**, correo en Office 365.
- Sensibles a privacidad y al catalán: la solución local encaja.

## Prioridad de procesos

1. Justicia gratuita (DNI, 12 nóminas, IRPF, empadronamiento…)
2. Honorarios (minutas y tasaciones con tablas)
3. Deontología y quejas (calidad variable, faxes)
4. Hemeroteca (Fòrum Jurídic)
5. Torn d'Ofici y arbitraje

## Funcionalidades

**Imprescindibles**: procesamiento 100 % local · interfaz CA por defecto y ES · bandeja con semáforo por página · revisión imagen/texto con dudas marcadas · exportación a PDF buscable y Word · SSO (extranet u Office 365) con perfiles · registro de accesos.

**Importantes**: checklist de justicia gratuita · ficha de datos extraídos · importación desde escáner y UNITRAM · búsqueda de texto completo · firma con ACA.

**Deseables**: resúmenes para comisiones · panel de volumen y tiempos.

> Principio: la herramienta ayuda a leer, no decide.

## Anonimización

Categorías (según CENDOJ y RGPD): nombres de personas físicas, documentos de identidad, direcciones, contacto, datos bancarios, menores (siempre), categorías especiales art. 9-10 (siempre), magistrados y funcionarios (configurable), matrículas (no por defecto), personas jurídicas (no), firmas y sellos en imagen.

Formas: censurar (por defecto), borrar, tachar (solo interno), etiqueta `[PERSONA 1]`, seudónimo, iniciales.

Garantías: borrado real en capa de texto, imagen y metadatos · confirmación humana antes de exportar · plantillas de reglas por tipo de documento · seudónimos cifrados y separados.

## Diseño

Sobrio, minimalista. Tokens: primario `#B2051B`, texto `#212121`, secundario `#5E5E5E`, fondo `#F6F5F3`, foco `#0B5CAD`; semáforo verde `#1F7A3A/#E6F4EA`, ámbar `#8A5A00/#FFF4D6`, rojo `#B2051B/#FBEDEF`. Roboto (UI), Roboto Condensed (navegación), Georgia (texto del documento). WCAG 2.2 AA. Navegación: Safata, Justícia gratuïta, Arxiu, Informes.

## Plan

| Fase | Contenido | Duración |
|---|---|---|
| 0 Validación | OCR con 100-200 páginas reales anonimizadas | 2-3 semanas |
| 1 Piloto | Bandeja, revisión, exportación; justicia gratuita en Tarragona | 6-8 semanas |
| 2 Extensión | Checklist, ficha, UNITRAM, honorarios, deontología, anonimización | 2-3 meses |
| 3 Archivo | Hemeroteca buscable | según prioridades |

## Preguntas para el ICAT

- Volumen mensual de expedientes de justicia gratuita y quejas, y páginas por expediente
- Cómo llega la documentación (papel, recepción, ciudadano)
- Quién revisa (secretaría, Comisión, colegiados)
- ¿Servidor propio con GPU?
- Quién mantiene UNITRAM y la extranet y qué integración ofrecen
- Peso del catalán en los documentos
- Interés en digitalizar Fòrum Jurídic
- Requisitos del DPD y la Secció TIC
