# Base de datos — modelo E/R v0.3

- **Fuente del modelo**: `Modelo-ER-POC-ICAT-v0.3` (`.docx`, `.pdf` y `.pptx`, 24/11/2026): 14 entidades, 19 relaciones con nombre, 23 FK internas y una referencia externa a la tabla de claves.
- **Diagrama vigente**: [[Modelo de datos]], alineado con esa versión.
- **Estado**: modelo objetivo. La edición actual de `V15` (`V1`–`V15`, [[0015-identidad-en-v15]]) crea ya las **14 tablas** y casi todas las columnas; quedan las diferencias de la sección final. Falta recrear la base de desarrollo para validarlas.
- **Detalle**: [diccionario de datos](../../docs/architecture/data-dictionary.md) y [arquitectura](../../docs/architecture/README.md).

## Tablas (14)

| Grupo | Tabla | Para qué | ¿En el SQL actual? |
|---|---|---|---|
| Identidad y acceso | `usuarios` | Persona del Colegio: email, SSO, estado, alta | Sí (`V1` + `V15`); sin `intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso` ni `password_cambiado_en` |
| | `usuarios_roles` | Roles N:M de cada usuario | Sí (`V15`); sin `otorgado_en` ni `otorgado_por` |
| | `sesiones_usuario` | Sesión propia, con caducidad y revocación | Sí (`V15`); con `ultimo_uso_en`, que la v0.3 no trae |
| Documento y OCR | `documentos` | Fichero subido, estado, cifrado y export | Sí; `hash_export` vive en la versión (B8) |
| | `paginas_documento` | Una fila por página: contraste y semáforo | Sí (`V14`) |
| | `versiones_documento` | Cada paso del documento y su motor | Sí (`V15` añade `es_actual`, `pipeline_version`, `confianza_layout_promedio` y `regla_id`) |
| | `bloques_layout` | Geometría y texto de cada bloque | Sí (`V14`) |
| Revisión y anonimización | `revisiones` | Cola de revisión, intentos y cierre optimista | Sí (`V7` + `V15`), con `documento_id` y `actualizado_en` |
| | `anotaciones_entidad` | Dato detectado, acción y decisión del revisor | Sí, con `regla_id` y FK compuesta por bloque/versión |
| | `categorias_sensibles` | Catálogo de datos a tapar y marca art. 9 RGPD | Sí, con timestamps desde `V15` |
| | `reglas_anonimizacion` | Regla versionada, una activa por código | Sí, con `UNIQUE (codigo, version)` desde `V15` |
| | `regla_categorias` | Qué categorías aplica cada regla y cómo | Sí (`V15`) |
| Sistema | `auditoria` | Registro encadenado de todo lo que pasa | Sí |
| | `configuracion_sistema` | Parámetros en JSON | Sí |

## Relaciones (19)

| Relación | Origen → destino | Cardinalidad |
|---|---|---|
| `tiene_rol` | `usuarios` → `usuarios_roles` | 1 : N |
| `abre` | `usuarios` → `sesiones_usuario` | 1 : N |
| `crea` | `usuarios` → `documentos` | 1 : N |
| `registra` | `usuarios` → `auditoria` | 1 : N |
| `actualiza` | `usuarios` → `configuracion_sistema` | 1 : N |
| `configura` | `usuarios` → `reglas_anonimizacion` | 1 : N |
| `valida` | `usuarios` → `anotaciones_entidad` | 1 : N |
| `asignado` | `usuarios` → `revisiones` | 1 : N |
| `genera` | `usuarios` → `versiones_documento` | 1 : N |
| `tiene_paginas` | `documentos` → `paginas_documento` | 1 : N |
| `tiene_versiones` | `documentos` → `versiones_documento` | 1 : N |
| `se_divide_en_bloques` | `versiones_documento` → `bloques_layout` | 1 : N |
| `genera_revisiones` | `versiones_documento` → `revisiones` | 1 : N |
| `aplica_regla` | `versiones_documento` → `reglas_anonimizacion` | N : 0..1 |
| `incluye` | `reglas_anonimizacion` → `regla_categorias` | 1 : N |
| `participa_en` | `categorias_sensibles` → `regla_categorias` | 1 : N |
| `clasifica` | `categorias_sensibles` → `anotaciones_entidad` | 1 : N |
| `produce` | `reglas_anonimizacion` → `anotaciones_entidad` | 1 : N |
| `contiene_entidades` | `bloques_layout` → `anotaciones_entidad` | 1 : N |

Las FK que no tienen relación nombrada en el diagrama de Chen son `usuarios_roles.otorgado_por` (tampoco existe en el SQL), `documentos.visto_bueno_por`, `anotaciones_entidad.version_id`, `revisiones.documento_id` y `documentos.clave_cifrado` (esta última apunta a una tabla de claves fuera del modelo).

## Diferencias que siguen abiertas (E-53)

- **`usuarios`**: la v0.3 trae `intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso` y `password_cambiado_en`; el SQL no los tiene. `sso_subject` es `UNIQUE` en ambos.
- **`usuarios_roles`**: la v0.3 trae `otorgado_en` y `otorgado_por`; el SQL solo guarda `(usuario_id, rol)`.
- **`sesiones_usuario`**: el SQL añade `ultimo_uso_en` (1 h deslizante), ausente en la v0.3.
- **`hash_export`**: la v0.3 lo pone en `documentos`; B8 cerró que el hash es de la versión (`versiones_documento.metadatos_proceso->>'hash_export'`).
- **Geometría legacy (E-51)**: `anotaciones_entidad` conserva `pagina_numero` y `bbox_*`, que no figuran en la v0.3.
- **Correcciones al modelo**: `documento_id` y `actualizado_en` son de `revisiones` (A-04 y A-23), y el parcial de A-04 es por documento.
- **A-20**: retirada el 18/11, aunque la v0.3 la diga «en pausa»; `fecha_limite` y `aviso_24h_enviado_en` quedan sin uso (E-42).

## Histórico

- 17/11: primer borrador del modelo de @Marina.
- 18/11: revisión con 0011 y la decisión de @Marina sobre los roles en tabla.
- 19/11: BD declarada definitiva (`V1`–`V15`); B8 cerrado y A-20 retirada.
- 24/11: versión 0.3 del documento de revisión, que es la fuente de esta ficha, y edición de `V15` con identidad, reglas y offsets por bloque.
- 25/11: E-21 y E-25 cerrados; los offsets cuentan dentro de `bloques_layout.contenido` con FK compuesta por versión.
