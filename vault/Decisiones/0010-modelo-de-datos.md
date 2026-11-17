# 0010 · Modelo de datos: una migración para lo que el contrato ya da por hecho

- **Estado**: Propuesta
- **Fecha**: 2026-11-17
- **Autor**: @ia-opencode-ruben
- **Se decide con**: @Marina (BD), @Rubén (backend)
- **Votos**: Faltan @Marina (BD) y @Rubén (backend).

## Contexto

El contrato y las reglas describen cosas que el esquema no tiene: autenticación con sesiones, bloques de layout con `bbox`, cola de revisión, semáforo por página y un hash del PDF. Son los bloqueantes B1, B3, B4, B5 y B8 de [[Coherencia]], y el detalle está en [`docs/pendientes.md`](../../docs/pendientes.md) §3.

Hoy las migraciones están ordenadas por *cuándo se escribió* cada tabla, no por *cuándo se necesita*. Eso da tres problemas: `usuarios` no aguanta el login, `bloques_layout` no existe aunque tres rutas la citan, y `revisiones` no cabe en una cola.

@Marina ha dibujado su propio modelo el 17/11. Está tal cual en [[Modelo de datos]], con la comparación punto por punto contra esta propuesta: lo que cierra, lo que deja abierto y los tres puntos donde las dos chocan (caducidad del expediente, dueño del hash del PDF y cola de revisión).

## Decisión

Se propone **no tocar retroactivamente V1-V12** y añadir tres migraciones nuevas, cada una con sus índices:

| # | Contenido | Depende de |
|---|---|---|
| `V13` | Identidad: `usuarios`, `tokens_usuario`, `sesiones_usuario` | [[0009-identidad]] |
| `V14` | Estructura: `bloques_layout`, `paginas_documento`, `documentos.num_paginas` | nada |
| `V15` | Flujo y export: estados, visto bueno, `revisiones`, hash, seeds | [[0005-reglas-usuarios-y-aprobacion]] y [[0007-generacion-pdf-final]] |

El orden importa: `V14` se puede escribir **hoy** y es la que desbloquea OCR, PDF y semáforo. `V13` no se toca hasta que se cierre 0009, porque la mitad de sus columnas dependen de si hay SSO o contraseña.

## Qué cambia, tabla a tabla

### `usuarios` (V13)

Hoy: `email`, `nombre_completo`, `rol`, `activo`. El contrato pide nombre y apellidos por separado, login y una cuenta con estados.

- `estado` (`invitado | activo | bloqueado | baja`) **sustituye** a `activo`. Motivo: el contrato distingue invitación, bloqueo y baja irreversible, y `activo boolean` solo puede expresar dos de los cuatro.
- `password_hash`, `password_cambiado_en`, `intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso`, `motivo_baja`: los piden las reglas U-04, U-08, U-13 y el `429` del login.
- `sso_subject` UNIQUE **solo si** 0009 elige SSO. Es el identificador del directorio del ICAT, no el email.
- El índice `idx_usuarios_rol_activo` pasa a `(rol, estado)`: al quitar `activo` se cae.

### `tokens_usuario` y `sesiones_usuario` (V13)

Tablas nuevas. `tokens_usuario` para invitación y reset (`tipo`, `token_hash`, `expira_en`, `usado_en`); `sesiones_usuario` para las sesiones (`token_hash`, `creado_en`, `revocado_en`), con el tope de 3 y desalojo de la más antigua.

Por qué nuevas y no columnas en `usuarios`: un usuario tiene varias sesiones y varios tokens a la vez, y el token se guarda **hasheado**. Con SSO, `tokens_usuario` se queda solo para el reset del admin de emergencia.

Se guarda el hash, nunca el token: el acceso se valida contra `token_hash` y la sesión se revoca marcando `revocado_en`.

### `documentos` (V14 y V15)

- `num_paginas`: el contrato lo devuelve en tres respuestas y no existe como columna.
- CHECK de `estado`: falta `pendiente_visto_bueno`, que la regla A-15 ya usa. Sin ampliarlo, el flujo de doble firma no se puede guardar.
- `visto_bueno_por`, `visto_bueno_en` y `cerrado_en`: A-15 y A-19 los nombran.
- Marca del original cifrado (decisión 0004): `ruta_almacenamiento` ya sirve para la ruta; falta saber con qué clave se descifra (KMS o columna), y eso es parte de lo que hay que decidir.
- `hash_export` y `exportado_en`: **uno solo de los dos sitios**. El diseño del PDF los pone en `versiones_documento.metadatos_proceso`; A-18 y el contrato, en `documentos`. Se propone que el dueño sea la **versión** (el PDF es por versión, y al reabrir el hash anterior debe sobrevivir) y que `documentos` solo guarde `estado` y `exportado_en`.

### `bloques_layout` (V14, tabla nueva)

`version_id`, `pagina`, `orden`, `label`, `bbox` y `contenido`. Es la entrada del PDF final y la base de los offsets de las anotaciones.

Por qué: sin ella no se puede reconstruir la maquetación ni rellenar el `bbox` que pide `GET /documents/{id}/versions/{version}/blocks`. Y fija **una** base para los offsets: hoy `anotaciones_entidad` los cuenta sobre el texto completo y el contrato sobre `bloques_layout.contenido`. Se propone la segunda, con `bloque_id` en la anotación.

### `paginas_documento` (V14, tabla nueva)

`documento_id`, `numero`, `contraste`, `estado`, `avisos`, `leida_ocr`. Es el semáforo de calidad por página, que hoy no tiene ni modelo ni endpoint (B5).

### `anotaciones_entidad` (V15)

- `bloque_id` y offsets dentro del bloque (ver arriba).
- CHECK de `accion_aplicada`: faltan censurar, etiqueta e iniciales (I1). El defecto del sistema pasa de `tachado` a censurar, porque `tachado` estaba reservado a uso interno.
- Las columnas `bbox_x/y/ancho/alto` se quedan solo si la base de offsets no basta para pintar la marca; si `bloques_layout` guarda el `bbox`, son redundantes.

### `revisiones` (V15)

- `revisor_id` pasa a **nulo**: la revisión nace en cola sin dueño (A-05) y la toma quien la cierra.
- `estado` admite `en_cola`.
- `asignado_a`, `asignado_en`, `fecha_limite`, `aviso_24h_enviado_en`: A-05 y A-20 (48 h laborables con aviso a las 24 h).

### Seeds y configuración (V15)

- `categorias_sensibles`: `NUSS` deja de ser `rgpd_especial`; es un identificador, no un dato del art. 9, y hoy dispara doble firma en cualquier expediente que lo mencione.
- `configuracion_sistema`: fuera los motores OCR en cloud (contradice [[0001-ocr-local-paddleocr-vl]]), `preservar_formato_pdf = false` (contradice 0007), fuera el «timeout de revisión de 60 min» (el plazo es 48 h) y `version_esquema_bd` corregido.

### Lo que **no** cambia

- `auditoria`: `evento` + `detalle` JSONB aguantan login, SSO, reapertura y export sin tocar la tabla.
- `versiones_documento`: la cadena `original → ocr_texto → anonimizado_ia → revisado_humano → final_aprobado` sirve tal cual.
- `reglas_anonimizacion` y `regla_categorias`: solo el seed del defecto.
- No hay borrado ni renombrado de tablas: nada de lo existente se pierde.

## Diagrama propuesto

```mermaid
erDiagram
    usuarios ||--o{ documentos : "crea"
    usuarios ||--o{ versiones_documento : "crea"
    usuarios ||--o{ revisiones : "revisa"
    usuarios ||--o{ sesiones_usuario : "abre"
    usuarios ||--o{ tokens_usuario : "recibe"

    documentos ||--|{ versiones_documento : "tiene"
    documentos ||--|{ paginas_documento : "tiene"
    versiones_documento ||--o{ bloques_layout : "se compone de"
    versiones_documento ||--o{ anotaciones_entidad : "contiene"
    versiones_documento ||--o{ revisiones : "se revisa en"
    bloques_layout ||--o{ anotaciones_entidad : "ubica"
    categorias_sensibles ||--o{ anotaciones_entidad : "clasifica"
    categorias_sensibles }o--o{ reglas_anonimizacion : "regla_categorias"

    usuarios {
        uuid id PK
        varchar email UK
        varchar nombre
        varchar apellidos
        varchar rol
        varchar estado "invitado, activo, bloqueado, baja"
        char password_hash "nulo si SSO"
        varchar sso_subject UK "solo si SSO"
        int intentos_fallidos
        timestamptz bloqueado_hasta
        timestamptz ultimo_acceso
        timestamptz password_cambiado_en
        text motivo_baja
    }
    sesiones_usuario {
        uuid id PK
        uuid usuario_id FK
        char token_hash UK
        inet ip
        text user_agent
        timestamptz creado_en
        timestamptz revocado_en "nulo mientras vive"
    }
    tokens_usuario {
        uuid id PK
        uuid usuario_id FK
        varchar tipo "invitacion o reset"
        char token_hash UK
        timestamptz expira_en
        timestamptz usado_en
    }
    documentos {
        uuid id PK
        char hash_sha256 UK
        varchar estado "incluye pendiente_visto_bueno"
        int num_paginas
        varchar ruta_almacenamiento
        varchar clave_cifrado "a decidir: KMS o columna"
        uuid visto_bueno_por FK
        timestamptz visto_bueno_en
        timestamptz cerrado_en
        timestamptz exportado_en
    }
    versiones_documento {
        uuid id PK
        uuid documento_id FK
        int numero_version
        varchar tipo_version
        text contenido_texto
        text contenido_html
        varchar ruta_pdf
        jsonb metadatos_proceso "hash_export y origen_geometria"
    }
    bloques_layout {
        uuid id PK
        uuid version_id FK
        int pagina
        int orden
        varchar label "titulo, parrafo, tabla"
        jsonb bbox "x, y, ancho, alto en puntos"
        text contenido
    }
    paginas_documento {
        uuid id PK
        uuid documento_id FK
        int numero
        int contraste "0-100, semaforo"
        varchar estado "ok, revisar, ilegible"
        jsonb avisos
        boolean leida_ocr
    }
    anotaciones_entidad {
        uuid id PK
        uuid version_id FK
        uuid bloque_id FK
        uuid categoria_id FK
        int inicio_offset "dentro del bloque"
        int fin_offset
        text texto_original
        varchar accion_aplicada
        varchar texto_sustitucion
        numeric confianza_deteccion
        varchar decision_revisor
    }
    revisiones {
        uuid id PK
        uuid version_id FK
        uuid revisor_id FK "nulo hasta que se toma"
        varchar estado "en_cola, en_proceso, aprobado, rechazado_con_cambios, devuelto"
        uuid asignado_a FK
        timestamptz asignado_en
        timestamptz fecha_limite "48 h laborables"
        timestamptz aviso_24h_enviado_en
    }
    categorias_sensibles {
        uuid id PK
        varchar codigo UK
        varchar nombre
        boolean rgpd_especial
    }
    reglas_anonimizacion {
        uuid id PK
        varchar codigo UK
        int version
        boolean activa
        varchar accion_por_defecto "propuesta: censurar"
    }
```

## Consecuencias

- Tres migraciones nuevas, ninguna destructiva. `V14` no espera a nadie; `V13` y `V15` esperan a 0009, 0005 y 0007.
- Los índices de V10 no se editan: se añaden en la migración que toca la columna (`idx_usuarios_rol_activo` en `V13`, los de `bloques_layout` y `paginas_documento` en `V14`).
- Si 0009 elige cuentas locales, `sesiones_usuario` y `tokens_usuario` son obligatorias; si elige SSO, `tokens_usuario` queda reducida al admin de emergencia.
- Si 0005 cambia las acciones de anonimización, el CHECK de `accion_aplicada` se abre en `V15` y no antes.
- `er-diagram.md` que cita `docs/architecture/README.md` no existe: este diagrama puede ser su punto de partida.

## Preguntas para @Marina

1. ¿`bloques_layout` guarda el `bbox` en puntos del PDF (595.3 × 841.9) o normalizado 0-1? Lo primero es lo que devuelve PyMuPDF; lo segundo sobrevive a un cambio de tamaño de página.
2. ¿`seudonimos` se crea ahora o se retira la promesa de la maqueta? Es la única tabla que añade superficie de cifrado (I2).
3. ¿`email` pasa a `citext` o se resuelve con un índice único sobre `lower(email)`? El contrato ya compara en minúsculas.
4. ¿La clave del original cifrado va a KMS o a una columna por documento? De eso depende si `documentos` necesita un campo más.
