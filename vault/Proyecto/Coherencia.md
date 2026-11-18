# Coherencia del proyecto — revisión del 16/11/2026

- **Estado**: abierta
- **Autor**: @ia-opencode-ruben
- **Alcance**: contrato v1 (`docs/api/endpoints.md`), reglas U/A (`docs/reglas/`), migraciones V1-V12, vistas y triggers, decisiones 0001-0007, `maqueta/index.html`, `README.md` y el plan de la [[Propuesta ICAT]].
- **Qué es**: la lista de contradicciones entre lo que promete el producto, lo que pide la maqueta y lo que aguantan el contrato y el modelo.
- **Qué no es**: no sustituye al [[Tablero]]. Cada bloqueante se cierra con una decisión o una tarea, no editando esta nota.

## Veredicto

El contrato va por delante del modelo en cuatro tablas y una veintena de columnas, la maqueta enseña tres productos a la vez y el plan de la propuesta deja la anonimización fuera del piloto. Nada es irresoluble: son ocho decisiones, no once semanas de código.

## Resuelto

| Fecha | Qué | Dónde |
|---|---|---|
| 16/11 | **A-15 ya no usa `nivel_riesgo`.** La doble firma se dispara con `rgpd_especial = true` (art. 9-10 RGPD). Con el seed actual, `nivel_riesgo = alto` incluía DNI, nombre, dirección e IBAN, así que todo expediente acababa en `pendiente_visto_bueno` y la regla dejaba de ser excepcional. | `docs/reglas/aprobacion.md` §7, `docs/api/endpoints.md` §9, [[0005-reglas-usuarios-y-aprobacion]] regla 6 |
| 16/11 | **La decisión del PDF final pasa de 0006 a 0007**: había dos 0006 en la bóveda y una era de Presidio. | [[0007-generacion-pdf-final]] |
| 16/11 | **El stack del backend no estaba escrito en ningún sitio**: solo se deducía de las dependencias del PDF. Queda en Propuesta, con Python + FastAPI como recomendación y C# como alternativa evaluada. | [[0008-stack-backend]] |

## Bloqueantes

No se puede implementar el contrato tal cual. Ordenados por lo que cuesta descubrirlos tarde.

| # | Qué no cuadra | Evidencia | Cómo se cierra | Quién |
|---|---|---|---|---|
| B1 | **No hay dónde guardar la autenticación.** Faltan `sesiones_usuario`, `tokens_usuario` y la contraseña; `usuarios` solo tiene `activo boolean`. Login, invitación, reset y el límite de 3 sesiones no se pueden construir | `V1__create_usuarios.sql` vs `docs/api/endpoints.md` §1; [[0005-reglas-usuarios-y-aprobacion]] §7 | Migración con `password_hash`, `estado`, `tokens_usuario` y `sesiones_usuario` | @Rubén, @Marina |
| B2 | **Dos sistemas de identidad.** La propuesta exige SSO Office 365; el contrato implementa contraseñas locales con invitación por email, y no hay proveedor de correo decidido. Desde el 18/11 el contrato ya tiene las dos rutas SSO propuestas y las de contraseña marcadas como camino de desarrollo | [[Propuesta ICAT]] vs `docs/api/endpoints.md` §1 | Propuesta en [[0009-identidad]] y [[0012-identidad-y-roles]]: SSO del ICAT sin gestión de cuentas y admin local solo de desarrollo. De eso depende B1 y el alta de usuarios | @Rubén, @Kevin, @Marina, @Alex |
| B3 | **`bloques_layout` no existe** en las migraciones, pero tres rutas y todo el PDF final dependen de ella. Además las anotaciones guardan offsets sobre el texto completo y su propio `bbox`, mientras el contrato dice que los offsets son dentro de `bloques_layout.contenido` y devuelve `bloque_id` | `docs/api/endpoints.md` §3-4 vs `V6__create_anotaciones_entidad.sql` | Crear `bloques_layout` y decidir la base de los offsets (una sola) | @Marina, @Rubén |
| B4 | **La cola de revisión no cabe en el modelo**: `revisiones.revisor_id` es `NOT NULL` y `estado` no admite `en_cola`; faltan `asignado_a`, `asignado_en`, `fecha_limite` y `aviso_24h_enviado_en` | `V7__create_revisiones.sql` vs `docs/reglas/aprobacion.md` §10 | Migración de `revisiones` y `documentos`; `revisor_id` pasa a nulo hasta que alguien toma la revisión | @Marina |
| B5 | **No hay endpoint para ver el original** —la pantalla central de la maqueta— ni modelo ni endpoint de **semáforo por página**, que es funcionalidad imprescindible de Fase 1 | `docs/api/endpoints.md` (no existe `GET .../original`); `V3__create_documentos.sql` sin `num_paginas` | `GET /documents/{id}/original` restringido y auditado; tabla de páginas con contraste, estado y avisos | @Rubén |
| B6 | **`expira_en` de 24 h mata el export.** La revisión tiene 48 h laborables de plazo y el export puede llegar días después; A-21 devuelve `404` a los endpoints de texto y PDF | `docs/reglas/aprobacion.md` §8 (A-21) vs §7 (A-16, A-18) | **Resuelto (17/11)**: `expira_en` fuera del expediente; A-21 lo deja como TTL de los temporales del OCR | @Rubén |
| B7 | **El visto bueno solo tiene camino feliz**: A-15 permite devolver a `en_revision` con motivo y la ruta devuelve `409`. Y A-18/A-19 hablan de reabrir un `aprobado`, pero `/reopen` solo acepta `rechazado` | `docs/reglas/aprobacion.md` §2, §7 vs `docs/api/endpoints.md` §6 | **En pausa con A-15 (18/11)**. Si se retoma: añadir la devolución al `sign-off` y decidir si un revisor puede reabrir un aprobado | @Rubén |
| B8 | **El hash del PDF está en dos sitios**: A-18 y el contrato lo ponen en `documentos.hash_export`; el diseño del PDF y la decisión 0007 lo ponen en `versiones_documento.metadatos_proceso->>'hash_export'`. El PDF es por versión: al reabrir, ¿de quién es el hash? | `docs/api/endpoints.md` §6, §10 vs `docs/export/pdf.md` §3 | Un solo dueño del hash, por versión, y `documentos` solo guarda estado y fecha | @Rubén |

## Importantes

| # | Qué no cuadra | Evidencia | Cómo se cierra |
|---|---|---|---|
| I1 | **Formas de anonimizar: 6 en la propuesta y la maqueta, 5 en el modelo** (`tachado`, `pseudonimizado`, `eliminado`, `mantenido`, `pendiente_revision`). Faltan censurar, etiqueta e iniciales. Y el defecto del sistema es `tachado`, que la propuesta reserva a uso interno | [[Propuesta ICAT]] §Anonimización, `V6`, `V12` | Ampliar el CHECK de `accion_aplicada` y cambiar `accion_por_defecto` a censurar |
| I2 | La maqueta promete «zonas de la imagen esborrades» y «taula de pseudònims xifrada i separada». La decisión 0007 no mete imagen y **no existe tabla de seudónimos**: una garantía del producto sin modelo | `maqueta/index.html` pantalla `#exportat`, [[0007-generacion-pdf-final]] | Cambiar el texto de la maqueta o crear la tabla de seudónimos cifrada |
| I3 | **El orden del flujo está invertido**: la maqueta revisa y valida antes de anonimizar; el contrato anonimiza y luego revisa. La decisión 0004 sigue abierta y su contexto está desactualizado | `maqueta` vs `docs/api/endpoints.md` §6, [[0004-anonimizacion-antes-o-despues-de-revision]] | Cerrar 0004 y reescribir su contexto |
| I4 | **El recorrido de la maqueta es imposible con los roles actuales**: una sola persona sube, revisa, anonimiza y exporta. Con roles múltiples ([[0012-identidad-y-roles]]) una cuenta puede hacer el recorrido entero, porque A-07 (nadie revisa lo suyo) está retirada y A-15 (otro revisor firma) en pausa | `docs/reglas/usuarios.md` §3, [[0005-reglas-usuarios-y-aprobacion]] | Ninguna: la demo puede ser de una sola persona. Si se retoman A-07 o A-15, vuelven a hacer falta dos |
| I5 | **OCR síncrono vs 23 páginas**: un request de ~30 s, riesgo de timeout. La maqueta muestra progreso asíncrono y «dos lecturas» que PaddleOCR-VL no produce: exigiría dos pasadas de OCR por página (~1.375 pág/h en vez de 2.750) | `docs/api/endpoints.md` §3, [[Rendimiento OCR]], `maqueta` pantalla `#revisio` | Decidir OCR asíncrono por página y si las dos lecturas se financian |
| I6 | **La pantalla de justicia gratuita no tiene contrato ni modelo**: checklist, datos extraídos, requerimiento y envío a UNITRAM. Y UNITRAM es una integración de proveedor desconocido | `maqueta` pantalla `#jg`, [[Propuesta ICAT]] §Preguntas | Fase 2 con contrato propio; no prometerla en el piloto |
| I7 | **Búsqueda de texto completo en Arxiu** sin endpoint ni índice: `GET /documents` solo filtra `estado` | `docs/api/endpoints.md` §3, `maqueta` `#arxiu` | Añadir `?q=` con `tsvector` cuando exista la tabla de páginas |
| I8 | El botón «Exportar PDF» de la revisión está activo antes de aprobar, justo lo que A-17 prohíbe | `maqueta/index.html` pantalla `#revisio` | Quitarlo o deshabilitarlo en la maqueta |
| I9 | **Nombres de ruta fuera de convención**: `visto-bueno` es el único segmento en castellano; `{usuario_id}` y `{numero}` mezclan idioma; `DELETE /admin/sessions/{usuario_id}` debería colgar del usuario | `docs/api/endpoints.md` resumen | **Resuelto (17/11)**: `sign-off`, `{numero_version}` y `DELETE /admin/users/{id}/sessions` |

## Higiene

| # | Qué | Dónde |
|---|---|---|
| H1 | El README sigue listando `/user/register`, que ya no existe, y promete exportación a Word | `README.md` §Endpoints, §Qué hace |
| H2 | El README no menciona `docs/api/`, `docs/reglas/` ni `docs/export/` en el árbol del repo | `README.md` §Estructura |
| H3 | RGPD: usa `estado = 'eliminado'`, que no está en el CHECK de `documentos`; borra `anotaciones_entidad` en cascada (choca con la trazabilidad de A-18); cita `usuarios.activo` | `docs/architecture/rgpd-considerations.md` |
| H4 | El README de arquitectura cita `er-diagram.md` (no existe) y «7 triggers» (hay 15) | `docs/architecture/README.md` |
| H5 | `usuarios.md` dice que `sesiones_usuario.creado_en` «ya existe»; la tabla no existe | `docs/reglas/usuarios.md` §7 |
| H6 | V12 siembra motores OCR en cloud (contradice 0001), `preservar_formato_pdf = true` (contradice 0007), `tiempo_max_revision_minutos = 60` (contradice el plazo de 48 h) y `version_esquema_bd = 1` con 12 migraciones | `V12__seed_configuracion_inicial.sql` |
| H7 | `vault/Inicio.md` escribe `Investigacion/` y la carpeta es `investigacion/`: en Linux rompe | `vault/Inicio.md` |
| H8 | `categorias_sensibles` marca `NUSS` como `rgpd_especial`: es un identificador, no un dato del art. 9, y ahora dispara doble firma | `V11__seed_categorias_sensibles.sql` |
| H9 | **No había stack de backend escrito**: ni lenguaje, ni framework, ni driver, ni dónde se despliega. Solo `reportlab` en el diseño del PDF. Resuelto como propuesta en [[0008-stack-backend]] | `README.md`, `docs/architecture/README.md` |

## La maqueta contra el plan

La propuesta reparte el trabajo así: Fase 0 validación (2-3 semanas), Fase 1 piloto (6-8 semanas: bandeja, revisión, exportación, justicia gratuita) y Fase 2 (2-3 meses: checklist, ficha, UNITRAM, honorarios, deontología **y anonimización**).

| Pantalla | Fase del plan | Lo que falta | Estimación |
|---|---|---|---|
| `#login` | 1 | Registro de app en el ICAT y OIDC (B1, B2) | 1-2 semanas |
| `#safata` | 1 | Subida, almacenamiento, estados y semáforo | 1 semana |
| `#processant` | 1 | OCR asíncrono y 4 en paralelo | 2 semanas |
| `#revisio` | 1 | Visor del original, estado por página, avisos y edición | 3 semanas |
| `#jg` | **2** | Checklist, extracción, requerimiento y UNITRAM | 4-6 semanas |
| `#anonimitzar` | **2** | Presidio, reglas y seis formas de anonimizar | 3-4 semanas |
| `#exportat` | 1-2 | Implementar el diseño de 0007 | 1-2 semanas |
| `#arxiu`, `#informes` | 2-3 | Búsqueda de texto completo y panel | 1-2 semanas |

**Conclusión:** la maqueta entera es construible, pero son **3-4 meses de trabajo efectivo**, no las 6-8 semanas del piloto. La Fase 1 cubre de verdad las pantallas 1-4 y un export básico. La anonimización, que es el 80 % de la demo del viernes, está en Fase 2; y la pantalla de justicia gratuita depende de UNITRAM, la mayor incógnita externa.

Hay además un problema de fondo: el plan pone la anonimización al final, pero el producto, el README, Presidio y las decisiones 0001/0005/0007 giran alrededor de ella. O se adelanta a Fase 1, o la demo del viernes debe ser de transcripción y justicia gratuita. Las dos a la vez no caben.

Detalle menor pero elocuente: en la maqueta el «escaneo» es HTML, no una imagen. Por eso puede marcar la palabra exacta al señalar un aviso (PR #6). Con un escaneo real eso exige coordenadas por palabra, que el OCR actual no da.

## Cómo se cierra

0. **Stack** (H9): decidir Python + FastAPI o C# en [[0008-stack-backend]] antes de escribir el primer endpoint. Es barato hoy y caro después.
1. **Nombres de ruta** (I9): antes de Figma y antes del frontend. Sin código, seis ficheros.
2. **Identidad** (B1, B2): es la decisión que desbloquea el resto del alta de usuarios. Con [[0012-identidad-y-roles]]: SSO, tres roles y roles múltiples.
3. **Modelo** (B1, B3, B4, B5, B8): tres migraciones —`V13` identidad, `V14` estructura, `V15` flujo— propuestas en [[0010-modelo-de-datos]]. El detalle de qué cambia en cada tabla está en [`docs/pendientes.md`](../../docs/pendientes.md) §3.
4. **Export** (B6, B8): un solo dueño del hash y quitar `expira_en` del expediente.
5. **Flujo** (B7, I1, I3): cerrar 0004 y decidir qué pasa al devolver un visto bueno.
6. **Maqueta** (I2, I4, I8): tres textos y un botón; y decidir si la demo va con una o dos personas.
7. **Higiene** (H1-H8): media hora, y evita que el README contradiga al contrato en la entrega del viernes.
