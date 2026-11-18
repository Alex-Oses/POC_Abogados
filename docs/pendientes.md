# Lo que falta antes de escribir el modelo

- **Estado:** abierto · 17/11/2026
- **Autor:** @ia-opencode-ruben
- **Para qué:** el contrato y las reglas ya describen autenticación, bloques de layout, cola de revisión y export; el esquema real (`docs/architecture/migrations/`) todavía no. Esto es lo que hay que **decidir o migrar** antes de escribir backend: identidad, geometría del PDF y todo lo que cambia en la base de datos.
- **Qué no es:** no decide nada. Los bloqueantes se citan por su ID de [Coherencia](../vault/Proyecto/Coherencia.md) y las decisiones por su número; aquí solo se agrupa lo que hoy no se puede implementar.
- **Verificado el 17/11/2026** contra las migraciones `V1`-`V12`, `docs/api/endpoints.md`, `docs/reglas/` y las decisiones 0001-0010. Si cambia cualquiera de esos cuatro, revisa la tabla de §3 (ver §6).

## 1. Identidad y sesiones (B1, B2 · [0009](../vault/Decisiones/0009-identidad.md))

**Dónde estamos.** `V1__create_usuarios.sql` tiene `email`, `nombre_completo`, `rol`, `activo`. El contrato pide contraseña, invitación por token, login, reset, tres sesiones simultáneas y una cuenta con estados (`invitado | activo | bloqueado | baja`). `docs/reglas/usuarios.md` §7 ya escribió la lista; el modelo no la tiene.

**Qué falta decidir.** [0009](../vault/Decisiones/0009-identidad.md) está en Propuesta: SSO del ICAT, cuentas locales o SSO + admin local de emergencia. Voto de @Rubén por la tercera; faltan @Kevin, @Marina y @Alex. Y hay una dependencia externa que no vota nadie del equipo: **el ICAT tiene que registrar la aplicación OIDC** (redirect URI, secreto, grupos). Son 1-2 semanas de terceros; si no llegan, la opción de cuentas locales sigue valiendo para el piloto y no cierra la puerta al SSO.

**Qué arrastra a la BD**

| Tabla | Qué se crea o cambia | Lo pide |
|---|---|---|
| `usuarios` | `roles TEXT[]` con `CHECK` de tres valores e índice GIN (sin tabla N:M); `estado` sustituye a `activo`; `nombre` y `apellidos` separados; `password_hash` (nulo si SSO), `password_cambiado_en`, `intentos_fallidos`, `bloqueado_hasta`, `ultimo_acceso`, `motivo_baja` y `sso_subject` (UNIQUE) si hay SSO | U-01, U-04, U-08, contrato §1-2, 0009, 0012 |
| `tokens_usuario` (nueva) | **no se crea**: U-10 a U-15 retiradas (18/11) y la contraseña del admin de desarrollo viene de variable de entorno (U-21) | — |
| `sesiones_usuario` (nueva) | `usuario_id`, `token_hash`, `creado_en`, `revocado_en`, `ip`, `user_agent`; tope de 3 con desalojo de la más antigua. **Solo si no se delega la sesión en el ICAT** | U-17, contrato §1, 0012 |
| `idx_usuarios_rol_activo` | se cae con `rol`/`activo`; entran `(estado)` y GIN `(roles)` | B1, 0012 |

Con SSO, `password_hash` queda **solo** para el admin de desarrollo y la invitación por email desaparece; `tokens_usuario` no se crea. Eso importa porque **no hay proveedor de correo elegido** (B2): sin invitaciones ni reset no hace falta SMTP.

**Qué no se puede escribir hasta decidir:** el alta de usuarios, el middleware de sesión y la pantalla de login. Sin U-10 a U-15 no queda ninguna caducidad de token de invitación o reset; la del expediente se retiró (B6, A-21).

## 2. `bbox`, OCR y reconstrucción del PDF (B3, I5 · [0007](../vault/Decisiones/0007-generacion-pdf-final.md) y [pdf.md](export/pdf.md))

**Decidido.** El PDF final se **reconstruye**: lienzo nuevo y texto nuevo, sin un píxel del escaneo. No es estética, es que el PDF es lo único que sale del despacho y no puede llevar capa oculta, metadatos ni una zona sin censurar. Se acepta la contrapartida: sellos, firmas manuscritas y textura no se reproducen.

**El hueco.** `bloques_layout` **no existe** en las migraciones, pero tres rutas y todo el PDF dependen de ella (B3). Además, las anotaciones guardan offsets sobre el texto completo y su propio `bbox`, mientras el contrato dice que los offsets son dentro de `bloques_layout.contenido` y devuelve `bloque_id`. Y el OCR actual —PaddleOCR-VL por Ollama, prompt `OCR:`— devuelve **texto sin coordenadas**: hoy nada puede rellenar el `bbox` que pide la API.

**La salida acordada (17/11).** No se elige una fuente de geometría: se decide **por documento**, en este orden y quedándose con la primera que funcione.

1. **Capa de texto del PDF subido** (PyMuPDF `page.get_text("dict")`): caja, tamaño y origen reales, sin OCR y en milisegundos.
2. **Modelo de layout** (pipeline completo de PaddleOCR/PP-Structure, o `docling`): una pasada más por página.
3. **Modo secuencial**: mismo orden y jerarquía, sin posiciones.

Lo aplicado queda en `origen_geometria` para que el render sea reproducible.

**Lo que falta antes de implementar:**

1. **Medir el corpus real**: qué proporción de los documentos del Colegio llega como PDF con texto. Sin ese dato no se sabe si la rama 2 se paga.
2. **Crear `bloques_layout`** y fijar **una** base para los offsets (propuesta: dentro de `contenido` del bloque, con `bloque_id` en la anotación).
3. **Decidir si el OCR es asíncrono por página** (I5) y si la demo necesita «dos lecturas»: cuesta el doble de OCR (~1.375 pág/h en vez de 2.750).
4. **Semáforo por página** (B5): sin el contraste guardado no se puede pintar; necesita la tabla de páginas.

**Lo que no cambia:** 0007, el JSON de estructura y el render. Cuando llegue el `bbox`, se rellena el mismo JSON y no se toca el código de dibujo.

## 3. Todo lo que cambia en la BD

| Tabla | Qué falta o cambia | Lo pide | Depende de |
|---|---|---|---|
| `usuarios` | estado, contraseña, SSO, intentos y último acceso | B1 | 0009 |
| `tokens_usuario` | **no se crea**: U-10 a U-15 retiradas (18/11); la contraseña del admin de desarrollo viene de variable de entorno | — | — |
| `sesiones_usuario` | tabla nueva, solo si no se delega la sesión en el ICAT | B1 | 0009, 0012 |
| `documentos` | `num_paginas` | B5 | — |
| `documentos` | CHECK de `estado`: falta `pendiente_visto_bueno`; decidir si hace falta un estado de reapertura | A-15, A-19, B7 | 0005 |
| `documentos` | `visto_bueno_por`, `visto_bueno_en`, `cerrado_en` | A-15, A-19 | 0005 |
| `documentos` | `hash_export` y `exportado_en`: o se quedan aquí o se van a la versión, **un solo dueño** | B8 | 0007 |
| `documentos` | marca del original cifrado y de su clave (KMS o columna) | 0004 | — |
| `versiones_documento` | `hash_export` y `exportado_en` si B8 se resuelve por versión | B8 | 0007 |
| `bloques_layout` | tabla nueva: `version_id`, `pagina`, `orden`, `label`, `bbox`, `contenido` | B3 | 0007 |
| `paginas_documento` | tabla nueva: documento, número, contraste, estado, avisos, si se leyó | B5, I5 | — |
| `anotaciones_entidad` | `bloque_id`; base única de offsets; CHECK de `accion_aplicada` con censurar, etiqueta e iniciales; qué pasa con `bbox_x/y/ancho/alto` | B3, I1 | 0007 |
| `revisiones` | `revisor_id` a nulo; estado `en_cola`; `asignado_a`, `asignado_en`, `fecha_limite`, `aviso_24h_enviado_en` | B4, A-05, A-20 | 0005 |
| `reglas_anonimizacion` | `accion_por_defecto` pasa de `tachado` a censurar | I1 | 0005 |
| `configuracion_sistema` (seed) | quitar motores OCR en cloud, `preservar_formato_pdf = false`, fuera el «timeout de 60 min» (el plazo es 48 h laborables) y corregir `version_esquema_bd` | H6 | — |
| `categorias_sensibles` (seed) | `NUSS` deja de ser `rgpd_especial`: es un identificador, no un dato del art. 9 | H8 | — |
| `seudonimos` | tabla nueva y cifrada **solo si** se mantiene la promesa de la maqueta («taula de pseudònims xifrada i separada») | I2 | 0005, 0007 |
| `auditoria` | **no cambia**: `evento` + `detalle` JSONB aguantan login, SSO, reapertura y export | — | — |

### Migraciones mínimas

| # | Contenido | Se puede empezar |
|---|---|---|
| V13 | Identidad: `usuarios`, `tokens_usuario`, `sesiones_usuario`, índices | **No**: espera 0009 |
| V14 | Estructura: `bloques_layout`, `paginas_documento`, `num_paginas`, índices | **Escrita** (`V14__create_bloques_layout.sql`): no depende de identidad |
| V15 | Flujo y export: estados, columnas del visto bueno, `revisiones`, seeds corregidos | **Escrita** (`V15__flujo_revision_y_export.sql`), salvo el hash: espera 0005 |
| V16 | Hash del PDF (B8), cuando se decida el dueño | No: espera B8 |

Los once puntos revisados, las cinco preguntas contestadas y el orden están en [`vault/Decisiones/0011-ajustes-al-modelo-de-marina.md`](../vault/Decisiones/0011-ajustes-al-modelo-de-marina.md).

## 4. Qué espera a quién

| Decisión | Quién falta | Desbloquea |
|---|---|---|
| [0009](../vault/Decisiones/0009-identidad.md) identidad | @Kevin, @Marina, @Alex | V13 y todo el alta de usuarios |
| [0008](../vault/Decisiones/0008-stack-backend.md) stack | @Marina, @Kevin, @Alex | el primer endpoint |
| [0005](../vault/Decisiones/0005-reglas-usuarios-y-aprobacion.md) reglas de usuarios y aprobación | @Rubén | estados, cola de revisión, reglas (V15) |
| [0007](../vault/Decisiones/0007-generacion-pdf-final.md) PDF final | @Rubén | `bloques_layout` y el export |
| [0006](../vault/Decisiones/0006-presidio-anonimizacion-local.md) Presidio | @Alex | acciones de anonimización (I1) |
| [0002](../vault/Decisiones/0002-postgresql.md) PostgreSQL + Flyway | equipo | ya se da por hecho en todo el repo |

## 5. Riesgos, por orden de lo que cuesta descubrir tarde

1. **Escribir el esquema antes de 0009** obliga a rehacer el alta y la sesión. Es el único punto donde esperar sale gratis.
2. **Arreglar los offsets después** de cargar anotaciones significa migrar datos y reescribir la revisión. `bloques_layout` va **antes** que el primer documento real.
3. **El `bbox` no es un problema de OCR**: se resuelve leyendo el PDF original. Lo caro sería dar por hecho que no hay capa de texto sin medirlo.
4. **El SSO es una dependencia externa**, no una tarea. Si el ICAT no registra la app, el piloto arranca con cuentas locales: la decisión 0009 ya lo contempla.
5. **Cada migración nueva toca los índices de V10** (`idx_usuarios_rol_activo` cae con `activo`). Los índices van en la misma migración que la columna, no en otra.

## 6. Cómo mantenerlo

Este informe **se queda obsoleto en cuanto entra una migración**, y una lista vieja es peor que ninguna. Se actualiza solo cuando pasa una de estas cuatro cosas; si no, no hace falta tocarlo:

| Cuándo | Qué hay que revisar |
|---|---|
| Se acepta una decisión (0005, 0007, 0009) | Las filas de §3 con «depende de» esa decisión pasan a tener respuesta |
| Entra una migración nueva (`V13`, `V14`, `V15`) | Borra sus filas de §3; si la tabla ya existe, deja de ser una propuesta |
| Cambia `docs/api/endpoints.md` o `docs/reglas/` | La columna «lo pide» puede apuntar a una regla que ya no existe o a una nueva |
| Cambia la numeración de las decisiones | Los enlaces de §1, §2 y §4 |

La fuente de verdad no es este documento: son las migraciones, el contrato y las reglas. Esto es solo el índice de lo que falta. Si la tabla de §3 y el esquema se contradicen, manda el esquema y lo que está mal es este informe.
