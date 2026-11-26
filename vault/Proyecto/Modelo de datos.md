# Modelo de datos

- **Qué es**: el modelo objetivo del proyecto, alineado con **`Modelo-ER-POC-ICAT-v0.3` (24/11/2026)**: 14 entidades, 19 relaciones con nombre y 23 FK internas más una referencia externa a la tabla de claves.
- **Fuente**: el `.docx`, `.pdf` y `.pptx` de la v0.3. Sustituye al diagrama que @Marina dibujó el 17/11 y a la revisión del 18/11; ambos quedan en el historial de git.
- **Estado**: es el **modelo objetivo**. La edición actual de `V15` ya crea las **14 tablas** (incluidas `usuarios_roles`, `sesiones_usuario` y `regla_categorias`, [[0015-identidad-en-v15]]) y casi todas las columnas de aquí; quedan las diferencias que se listan en «Lo que sigue abierto».
- **Los bloqueantes** se citan por su ID de [[Coherencia]] (B1-B8, I1-I9) y las reglas por su código (`docs/reglas/`). B1, B3 y B8 están cerrados; B5 tiene lector; I2 sigue abierta.

## Diagrama

```mermaid
erDiagram
    USUARIOS {
        uuid id PK
        varchar email UK "unico"
        varchar password_hash "solo admin de desarrollo"
        varchar nombre
        varchar apellidos
        varchar estado "activo, bloqueado, baja"
        text motivo_baja
        int intentos_fallidos
        timestamptz bloqueado_hasta
        timestamptz ultimo_acceso
        timestamptz password_cambiado_en
        timestamptz creado_en
        timestamptz actualizado_en
        varchar sso_subject UK "sub del SSO del ICAT"
    }

    USUARIOS_ROLES {
        uuid usuario_id PK, FK "usuarios.id"
        varchar rol PK "admin, transcriptor, revisor"
        timestamptz otorgado_en
        uuid otorgado_por FK "usuarios.id: quien lo otorgo"
    }

    SESIONES_USUARIO {
        uuid id PK
        uuid usuario_id FK "usuarios.id"
        varchar token_hash UK
        inet ip_origen
        timestamptz expira_en
        timestamptz revocado_en
        timestamptz creado_en
        text user_agent
    }

    DOCUMENTOS {
        uuid id PK
        varchar nombre_original
        varchar hash_sha256
        varchar mime_type
        bigint tamano_bytes
        int num_paginas
        varchar ruta_almacenamiento
        varchar estado "pendiente ... exportado"
        timestamptz eliminado_en "borrado logico"
        boolean requiere_visto_bueno
        uuid visto_bueno_por FK "usuarios.id"
        timestamptz visto_bueno_en
        timestamptz cerrado_en
        varchar hash_export
        timestamptz exportado_en
        jsonb metadatos_extras
        uuid creado_por FK "usuarios.id"
        timestamptz creado_en
        timestamptz actualizado_en
        uuid clave_cifrado "id de la clave; el material, fuera de la BD"
    }

    PAGINAS_DOCUMENTO {
        uuid id PK
        uuid documento_id FK "documentos.id"
        int numero UK "unico por documento"
        int contraste "0-100; por debajo de 80 no se transcribe"
        varchar estado "ok, revisar, ilegible"
        jsonb avisos
        boolean leida_ocr
        timestamptz creado_en
    }

    VERSIONES_DOCUMENTO {
        uuid id PK
        uuid documento_id FK "documentos.id"
        int numero_version UK "unico por documento"
        varchar tipo_version "original, ocr, anonimizado, revisado, final"
        text contenido_texto
        text contenido_html
        varchar ruta_pdf
        varchar motor_ocr
        varchar modelo_ia
        varchar pipeline_version
        decimal confianza_layout_promedio
        jsonb metadatos_proceso
        uuid regla_id FK "reglas_anonimizacion.id; nulo si no aplica"
        boolean es_actual
        uuid creado_por FK "usuarios.id"
        timestamptz creado_en
    }

    BLOQUES_LAYOUT {
        uuid id PK
        uuid version_id FK "versiones_documento.id"
        int pagina_numero UK "clave (version_id, pagina_numero, orden_lectura)"
        int orden_lectura UK
        varchar etiqueta
        decimal confianza
        varchar forma
        decimal bbox_x
        decimal bbox_y
        decimal bbox_ancho
        decimal bbox_alto
        decimal pagina_ancho
        decimal pagina_alto
        jsonb puntos
        text contenido
        varchar calidad_semaforo "verde, amarillo, rojo"
        timestamptz creado_en
    }

    REVISIONES {
        uuid id PK
        uuid version_id FK "versiones_documento.id"
        uuid documento_id FK "A-04: unico parcial por documento"
        uuid asignado_a FK "usuarios.id; nulo mientras esta en cola"
        timestamptz asignado_en
        varchar estado "en_cola, en_proceso, aprobado, rechazado_con_cambios, devuelto"
        int numero_intento
        int tiempo_revision_seg
        text comentario_general "obligatorio al rechazar"
        timestamptz fecha_limite "A-20 retirada: sin uso"
        timestamptz aviso_24h_enviado_en "A-20 retirada: sin uso"
        timestamptz creado_en
        timestamptz actualizado_en "A-23: If-Match"
        timestamptz finalizado_en
    }

    ANOTACIONES_ENTIDAD {
        uuid id PK
        uuid version_id FK "versiones_documento.id"
        uuid categoria_id FK "categorias_sensibles.id"
        uuid bloque_id FK "bloques_layout.id"
        uuid regla_id FK "reglas_anonimizacion.id; nulo si no aplica"
        int inicio_offset "indice dentro de bloques_layout.contenido"
        int fin_offset
        text texto_original
        varchar accion_aplicada "censurar, etiqueta, iniciales, pseudonimizado, eliminado, mantenido, tachado, pendiente_revision"
        text texto_sustitucion
        decimal confianza_deteccion
        varchar motor_deteccion "regex, ner, llm, manual"
        uuid revisado_por FK "usuarios.id"
        timestamptz revisado_en
        varchar decision_revisor "confirmado, modificado, falso_positivo, falso_negativo"
        text observaciones_revisor
        timestamptz creado_en
    }

    CATEGORIAS_SENSIBLES {
        uuid id PK
        varchar codigo UK
        varchar nombre
        text descripcion
        text regex_patron
        int prioridad "orden si dos categorias solapan"
        varchar nivel_riesgo "alto, medio, bajo"
        boolean rgpd_especial "art. 9 RGPD"
        boolean activa
        timestamptz creado_en
        timestamptz actualizado_en
    }

    REGLAS_ANONIMIZACION {
        uuid id PK
        varchar codigo UK "junto con version: (codigo, version)"
        int version UK
        varchar nombre
        text descripcion
        boolean activa "una sola activa por codigo"
        uuid creado_por FK "usuarios.id"
        timestamptz creado_en
        timestamptz actualizado_en
    }

    REGLA_CATEGORIAS {
        uuid regla_id PK, FK "reglas_anonimizacion.id"
        uuid categoria_id PK, FK "categorias_sensibles.id"
        jsonb configuracion "accion, umbral, excepciones"
    }

    AUDITORIA {
        bigserial id PK
        varchar evento
        varchar entidad_tipo
        uuid entidad_id
        uuid usuario_id FK "usuarios.id"
        inet ip_origen
        text user_agent
        jsonb detalle "incluye la clave de la entidad"
        varchar hash_anterior "cadena de integridad"
        timestamptz creado_en
    }

    CONFIGURACION_SISTEMA {
        varchar clave PK
        jsonb valor
        text descripcion
        uuid actualizado_por FK "usuarios.id"
        timestamptz creado_en
        timestamptz actualizado_en
    }

    USUARIOS ||--o{ USUARIOS_ROLES : "tiene_rol"
    USUARIOS ||--o{ SESIONES_USUARIO : "abre"
    USUARIOS |o--o{ DOCUMENTOS : "crea"
    USUARIOS |o--o{ AUDITORIA : "registra"
    USUARIOS |o--o{ CONFIGURACION_SISTEMA : "actualiza"
    USUARIOS |o--o{ REGLAS_ANONIMIZACION : "configura"
    USUARIOS |o--o{ ANOTACIONES_ENTIDAD : "valida"
    USUARIOS |o--o{ REVISIONES : "asignado"
    USUARIOS |o--o{ VERSIONES_DOCUMENTO : "genera"

    DOCUMENTOS ||--o{ PAGINAS_DOCUMENTO : "tiene_paginas"
    DOCUMENTOS ||--o{ VERSIONES_DOCUMENTO : "tiene_versiones"
    VERSIONES_DOCUMENTO ||--o{ BLOQUES_LAYOUT : "se_divide_en_bloques"
    VERSIONES_DOCUMENTO ||--o{ REVISIONES : "genera_revisiones"
    VERSIONES_DOCUMENTO }o--o| REGLAS_ANONIMIZACION : "aplica_regla"

    REGLAS_ANONIMIZACION ||--o{ REGLA_CATEGORIAS : "incluye"
    CATEGORIAS_SENSIBLES ||--o{ REGLA_CATEGORIAS : "participa_en"
    CATEGORIAS_SENSIBLES ||--o{ ANOTACIONES_ENTIDAD : "clasifica"
    REGLAS_ANONIMIZACION |o--o{ ANOTACIONES_ENTIDAD : "produce"
    BLOQUES_LAYOUT |o--o{ ANOTACIONES_ENTIDAD : "contiene_entidades"
```

## Qué cambia respecto a la revisión anterior de este diagrama (18/11)

| Bloque | Cambio |
|---|---|
| Relaciones | Las tres relaciones llamadas `tiene` pasan a 19 nombres únicos en `snake_case`: `tiene_rol`, `tiene_paginas`, `tiene_versiones`, etc. `aplica_regla` se escribe `N : (0..1)` |
| `USUARIOS` | Vuelven `intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso` y `password_cambiado_en`; sale `eliminado_en`; `password_hash` es `varchar` y `nombre`/`apellidos` van separados |
| `USUARIOS_ROLES` | Gana `otorgado_en` y `otorgado_por` (auto-referencia); los tres roles son `admin`, `transcriptor` y `revisor` |
| `SESIONES_USUARIO` | La v0.3 no incluye `ultimo_uso_en` (que sí añade `V15`); conserva `expira_en`, `revocado_en` y `user_agent` |
| `DOCUMENTOS` | Vuelve `hash_export`; la v0.3 no documenta el único parcial de `hash_sha256` por creador |
| `REVISIONES` | `documento_id` y `actualizado_en` pasan aquí desde `ANOTACIONES_ENTIDAD`; el parcial de A-04 es **por documento**, no por versión |
| `ANOTACIONES_ENTIDAD` | Salen `documento_id` y `actualizado_en`; los offsets cuentan dentro de `bloques_layout.contenido`, como dice la v0.3 |
| `REGLAS_ANONIMIZACION` y `REGLA_CATEGORIAS` | `codigo` y `version` forman el único `(codigo, version)`; la tabla puente tiene PK compuesta `(regla_id, categoria_id)` |
| `AUDITORIA` | `hash_anterior` se documenta como `varchar`, no `char(64)` |

## Dos correcciones aplicadas a la v0.3

La v0.3 arrastra dos errores que **no** se han copiado al diagrama:

1. Pone `documento_id` y `actualizado_en` en `ANOTACIONES_ENTIDAD`; son columnas de `REVISIONES` (índice de A-04 y `If-Match` de A-23, según `docs/reglas/aprobacion.md`).
2. Describe el índice parcial de A-04 «por versión»; la regla aceptada es **una revisión abierta por documento**.

## Lo que sigue abierto

- **Desfase con el SQL (E-53)**: la edición actual de `V15` ya trae las 14 tablas y casi todas las columnas, pero no tiene `intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso` ni `password_cambiado_en` en `usuarios`, ni `otorgado_en`/`otorgado_por` en `usuarios_roles`. Sí tiene, en cambio, `ultimo_uso_en` en `sesiones_usuario`, que la v0.3 no contempla.
- **`hash_export` (E-53)**: la v0.3 lo pone en `DOCUMENTOS` y da B8 por abierto. B8 está cerrado desde el 19/11: el hash es de la versión, en `versiones_documento.metadatos_proceso->>'hash_export'`. El diagrama recoge la columna por fidelidad a la v0.3, pero manda el acuerdo del equipo.
- **Offsets**: resueltos el 25/11 (B3, E-21). La v0.3 y la edición actual de `V15` coinciden: cuentan dentro de `bloques_layout.contenido` y `bloque_id` lleva FK compuesta por versión (E-25).
- **A-20**: la v0.3 la marca «en pausa»; está **retirada** desde el 18/11. `fecha_limite` y `aviso_24h_enviado_en` siguen en el SQL sin uso (E-42).
- **0012 en la v0.3 (E-53)**: su §5 dice que la propuesta sustituye `usuarios_roles` por una columna `roles`; está al revés. @Marina decidió el 18/11 que los roles van en tabla, y [[0015-identidad-en-v15]] lo implementa.
- **Identidad**: [[0009-identidad]] y la parte de [[0012-identidad-y-roles]] que afecta al modelo están implementadas al final de `V15` ([[0015-identidad-en-v15]]). Falta recrear la base de desarrollo y validar vistas, triggers y diccionario; el registro OIDC del ICAT sigue pendiente (B2).
- **Tabla de seudónimos (I2, E-38)**: `pseudonimizado` guarda `texto_sustitucion` en la anotación, así que la misma persona puede salir con dos seudónimos distintos en el mismo documento.
- **Geometría legacy (E-51)**: `anotaciones_entidad` conserva `pagina_numero` y `bbox_*`, que no aparecen en la v0.3. Queda decidir si se guardan como respaldo o se eliminan con plan de datos.

## Qué queda del debate con 0010

[[0010-modelo-de-datos]] proponía bajar el modelo en tres migraciones (`V13` identidad, `V14` estructura, `V15` flujo). `V14` y `V15` están escritas; `V13` se descartó al cerrar la BD el 19/11 y la identidad se añadió al final de `V15` ([[0015-identidad-en-v15]]). Su diagrama se retiró el 18/11 para dejar **un solo diagrama**, este, que ahora sigue la v0.3 del 24/11.

Lo que 0010 acertó y se ha quedado: `bloques_layout` como base de los offsets, `paginas_documento` con semáforo por página, la cola de revisión con `asignado_a`, las relaciones de reglas y un solo dueño del hash del PDF (B8).

**Fuentes**: `Modelo-ER-POC-ICAT-v0.3.docx`, `.pdf` y `.pptx` (24/11/2026, documentos de revisión); [[0010-modelo-de-datos]], [[0011-ajustes-al-modelo-de-marina]], [[0012-identidad-y-roles]] y [[0015-identidad-en-v15]].
