# Coherencia del proyecto — revisión del 16/11/2026

- **Estado**: abierta. La BD (`V1`-`V15`) es **definitiva** desde el 19/11: no hay plan de migrarla, así que cada bloqueante se cierra en el contrato o queda fuera del alcance.
- **Actualizado**: 20/11/2026. Los defectos comprobables viven en el [[Registro de errores]]; aquí quedan las contradicciones de producto.
- **Autor**: @ia-opencode-ruben
- **Alcance**: contrato v1 (`docs/api/endpoints.md`), reglas U/A (`docs/reglas/`), migraciones `V1`-`V15`, vistas y triggers, decisiones 0001-0012, `maqueta/index.html`, `README.md` y el plan de la [[Propuesta ICAT]].
- **Qué es**: la lista de contradicciones entre lo que promete el producto, lo que pide la maqueta y lo que aguantan el contrato y el modelo.
- **Qué no es**: no sustituye al [[Tablero]] ni al [[Registro de errores]]. Cada bloqueante se cierra con una decisión o una tarea, no editando esta nota.

## Veredicto

La revisión del 16/11 encontró cuatro bloqueantes y nueve importantes. Hoy queda **un bloqueante** (B1, la identidad) y cinco importantes abiertos (I4-I8). Lo demás se cerró con decisiones (0004, 0005, 0007, 0009), con `V14`/`V15` o con el contrato. Lo que sobrevive no pide migraciones.

## Resuelto

| Fecha | Qué | Dónde |
|---|---|---|
| 16/11 | **A-15 ya no usa `nivel_riesgo`.** La doble firma se dispara con `rgpd_especial = true` (art. 9-10 RGPD). Con el seed actual, `nivel_riesgo = alto` incluía DNI, nombre, dirección e IBAN, así que todo expediente acababa en `pendiente_visto_bueno` y la regla dejaba de ser excepcional. | `docs/reglas/aprobacion.md` §7, `docs/api/endpoints.md` §9, [[0005-reglas-usuarios-y-aprobacion]] regla 6 |
| 16/11 | **La decisión del PDF final pasa de 0006 a 0007**: había dos 0006 en la bóveda y una era de Presidio. | [[0007-generacion-pdf-final]] |
| 16/11 | **El stack del backend no estaba escrito en ningún sitio**: solo se deducía de las dependencias del PDF. Queda en Propuesta, con Python + FastAPI como recomendación y C# como alternativa evaluada. **Aceptada el 20/11 y reabierta el mismo día**: el ETL sale del backend y cae el argumento de un solo lenguaje; [[0014-stack-backend-c-sharp-java-python]] compara C#, Java y Python | [[0008-stack-backend]] |
| 19/11 | **README alineado con el contrato**: fuera `/user/register`, fuera la exportación a Word, árbol con `docs/api/`, `docs/reglas/` y `docs/export/`, migraciones `V1`-`V15` | `README.md` (H1, H2) |
| 19/11 | **Arquitectura sin referencias muertas**: `er-diagram.md` (no existe) → `diagrama-bbdd-borrador.png`; «7 triggers» → 16 | `docs/architecture/README.md` (H4) |
| 19/11 | **El semáforo por página y el original ya tienen ruta**: `GET /documents/{id}/pages` y `GET /documents/{id}/original` | `docs/api/endpoints.md` (B5) |
| 20/11 | **I1 cerrado por `V15`**: el `CHECK` de `accion_aplicada` pasa a 8 valores (`censurar`, `etiqueta`, `iniciales`, `pseudonimizado`, `eliminado`, `mantenido`, `tachado`, `pendiente_revision`) y `accion_por_defecto` pasa a `censurar` | `V15:110-118,151-154` |
| 20/11 | **H6 y H8 cerrados por `V15`**: motores OCR en local, `preservar_formato_pdf = false`, fuera `tiempo_max_revision_minutos`, `version_esquema_bd = 15` y `NUSS` deja de ser `rgpd_especial` | `V15:136-161` |
| 20/11 | **El contrato deja de pedir columnas que no existen** (E-31, E-32, E-35, E-37): sin `es_actual`, con `confianza_promedio`, estados de página de `V14` y export idempotente | `docs/api/endpoints.md` (PR #41) |
| 20/11 | **I2 y H5 cerrados**: la maqueta ya no promete «zones de la imatge esborrades» y `usuarios.md` ya no apunta a `V13` | `maqueta/index.html`, `docs/reglas/usuarios.md` (PR #41) |

## Bloqueantes

No se puede implementar el contrato tal cual. Ordenados por lo que cuesta descubrirlos tarde.

| # | Qué no cuadra | Evidencia | Cómo se cierra | Quién |
|---|---|---|---|---|
| B1 | **No hay dónde guardar la autenticación.** Falta la contraseña, el estado, el `sso_subject` y los roles; `usuarios` solo tiene `rol` de un valor y `activo boolean`. El diseño de [[0012-identidad-y-roles]] pide `estado` y `sso_subject` en `usuarios`, `usuarios_roles` para los roles (decisión de @Marina, 18/11) y `sesiones_usuario`; `tokens_usuario` no se crea | `V1__create_usuarios.sql` vs `docs/api/endpoints.md` §1; [[0005-reglas-usuarios-y-aprobacion]] §7 | **Con la BD cerrada no habrá `V13`**: decidir si se implementa sobre `rol`/`activo` o queda fuera del piloto | @Rubén, @Marina |
| B2 | **Dos sistemas de identidad.** La propuesta exige SSO Office 365; el contrato implementaba contraseñas locales con invitación por email, y no hay proveedor de correo decidido. Desde el 18/11 el contrato ya tiene las dos rutas SSO propuestas, las de contraseña marcadas como camino de desarrollo y la invitación y el reset retirados | [[Propuesta ICAT]] vs `docs/api/endpoints.md` §1 | **Resuelto (2026-11-20)**: 0009 aceptada (SSO + admin local solo de desarrollo, cuentas locales como alternativa). Queda el registro OIDC en el ICAT | @Rubén |
| B3 | **`bloques_layout` ya existe** (`V14`), pero `anotaciones_entidad` no tiene `bloque_id`: sus offsets van sobre el texto completo de la versión | `docs/api/endpoints.md` §3-4 vs `V6__create_anotaciones_entidad.sql` | **Resuelto (19/11)**: el contrato cuenta los offsets sobre `contenido_texto` y ya no devuelve `bloque_id`. Sin cambios de BD | @Rubén |
| B4 | **La cola de revisión no cabe en el modelo**: `revisiones.revisor_id` es `NOT NULL` y `estado` no admite `en_cola`; faltaban `asignado_a`, `asignado_en`, `fecha_limite` y `aviso_24h_enviado_en` | `V7__create_revisiones.sql` vs `docs/reglas/aprobacion.md` §10 | **Resuelto (17/11)**: `V15` renombra a `asignado_a`, lo deja nulo y añade `en_cola`. `fecha_limite` y `aviso_24h` existen pero **A-20 está retirada (18/11)** y se quedan sin uso | @Marina |
| B5 | **Falta el lector del semáforo.** `V14` ya trae `num_paginas` y `paginas_documento`, pero no había endpoint que las devolviera ni ruta para ver el original | `docs/api/endpoints.md` (no existía `GET .../pages` ni `GET .../original`) | **Resuelto (19/11)**: el contrato añade `GET /documents/{id}/pages` y `GET /documents/{id}/original` (auditado). Sin cambios de BD | @Rubén |
| B6 | **`expira_en` de 24 h mata el export.** La revisión tiene 48 h laborables de plazo y el export puede llegar días después; A-21 devuelve `404` a los endpoints de texto y PDF | `docs/reglas/aprobacion.md` §8 (A-21) vs §7 (A-16, A-18) | **Resuelto (17/11)**: `expira_en` fuera del expediente; A-21 lo deja como TTL de los temporales del OCR | @Rubén |
| B7 | **El visto bueno solo tiene camino feliz**: A-15 permite devolver a `en_revision` con motivo y la ruta devuelve `409`. Y A-18/A-19 hablan de reabrir un `aprobado`, pero `/reopen` solo aceptaba `rechazado` | `docs/reglas/aprobacion.md` §2, §7 vs `docs/api/endpoints.md` §6 | **Parcialmente resuelto (19/11)**: `/reopen` ya acepta `aprobado` con `comentario` (A-19). La devolución desde el visto bueno sigue en pausa con A-15 | @Rubén |
| B8 | **El hash del PDF está en dos sitios**: A-18 y el contrato lo ponen en `documentos.hash_export`; el diseño del PDF y la decisión 0007 lo ponen en `versiones_documento.metadatos_proceso->>'hash_export'`. El PDF es por versión: al reabrir, ¿de quién es el hash? | `docs/api/endpoints.md` §6, §10 vs `docs/export/pdf.md` §3 | **Resuelto (19/11)**: dueño único, la versión (`metadatos_proceso->>'hash_export'`); A-18 y el contrato corregidos. Sin cambios de BD | @Rubén |

## Importantes

| # | Qué no cuadra | Evidencia | Cómo se cierra |
|---|---|---|---|
| I1 | ~~**Formas de anonimizar: 6 en la propuesta y la maqueta, 5 en el modelo**; faltaban censurar, etiqueta e iniciales y el defecto era `tachado`~~ **Resuelto (20/11)**: `V15` deja 8 acciones en el `CHECK` y `accion_por_defecto = censurar` | `V15:110-118,151-154` | — |
| I2 | ~~La maqueta prometía «taula de pseudònims xifrada i separada» y luego «zones de la imatge esborrades»~~ **Resuelto (20/11, PR #41)**: la maqueta dice que el PDF se reconstruye desde el texto, sin el escaneo ni su capa de texto. Queda E-38 (seudónimos coherentes, sin mapa) en el [[Registro de errores]] | `maqueta/index.html` `#exportat`, [[0007-generacion-pdf-final]] | — |
| I3 | ~~**El orden del flujo está invertido**: la maqueta revisa y valida antes de anonimizar; el contrato anonimiza y luego revisa~~ **Resuelto**: 0004 es **Aceptada** desde el 17/11 y el contrato ya anonimiza antes de revisar | `maqueta` vs `docs/api/endpoints.md` §6, [[0004-anonimizacion-antes-o-despues-de-revision]] | — |
| I4 | **El recorrido de la maqueta es imposible con los roles actuales**: una sola persona sube, revisa, anonimiza y exporta. Con roles múltiples ([[0012-identidad-y-roles]]) una cuenta puede hacer el recorrido entero, porque A-07 (nadie revisa lo suyo) está retirada y A-15 (otro revisor firma) en pausa | `docs/reglas/usuarios.md` §3, [[0005-reglas-usuarios-y-aprobacion]] | Ninguna: la demo puede ser de una sola persona. Si se retoman A-07 o A-15, vuelven a hacer falta dos |
| I5 | **OCR síncrono vs 23 páginas**: un request de ~30 s, riesgo de timeout. La maqueta muestra progreso asíncrono. La doble lectura ya está decidida (A-24, 20/11): dos pasadas por página, diff en `metadatos_proceso` y avisos en `paginas_documento`, a ~1.375 pág/h en vez de 2.750 | `docs/api/endpoints.md` §3, [[Rendimiento OCR]], `maqueta` pantalla `#revisio` | **Parcialmente resuelto**: queda decidir el OCR asíncrono por página |
| I6 | **La pantalla de justicia gratuita no tiene contrato ni modelo**: checklist, datos extraídos, requerimiento y envío a UNITRAM. Y UNITRAM es una integración de proveedor desconocido | `maqueta` pantalla `#jg`, [[Propuesta ICAT]] §Preguntas | Fase 2 con contrato propio; no prometerla en el piloto |
| I7 | **Búsqueda de texto completo en Arxiu** sin endpoint ni índice: `GET /documents` solo filtra `estado` | `docs/api/endpoints.md` §3, `maqueta` `#arxiu` | Añadir `?q=` con `tsvector` cuando exista la tabla de páginas |
| I8 | El botón «Exportar PDF» de la revisión está activo antes de aprobar, justo lo que A-17 prohíbe | `maqueta/index.html` pantalla `#revisio` | Quitarlo o deshabilitarlo en la maqueta |
| I9 | **Nombres de ruta fuera de convención**: `visto-bueno` es el único segmento en castellano; `{usuario_id}` y `{numero}` mezclan idioma; `DELETE /admin/sessions/{usuario_id}` debería colgar del usuario | `docs/api/endpoints.md` resumen | **Resuelto (17/11)**: `sign-off`, `{numero_version}` y `DELETE /admin/users/{id}/sessions` |

## Higiene

| # | Qué | Dónde |
|---|---|---|
| H1 | ~~El README sigue listando `/user/register`, que ya no existe, y promete exportación a Word~~ **Resuelto (19/11)** | `README.md` §Endpoints, §Qué hace |
| H2 | ~~El README no menciona `docs/api/`, `docs/reglas/` ni `docs/export/` en el árbol del repo~~ **Resuelto (19/11)** | `README.md` §Estructura |
| H3 | RGPD: ~~usa `estado = 'eliminado'`, que no está en el CHECK~~ **el CHECK ya lo admite desde `V15`**. Siguen vivos el borrado en cascada de `anotaciones_entidad` (choca con A-18) y `usuarios.activo`; la acción por defecto y la retención son E-44 | `docs/architecture/rgpd-considerations.md` |
| H4 | ~~El README de arquitectura cita `er-diagram.md` (no existe) y «7 triggers» (hay 15)~~ **Resuelto (19/11)**: apunta al PNG y dice 16 | `docs/architecture/README.md` |
| H5 | ~~`usuarios.md` dice que `sesiones_usuario.creado_en` «ya existe»; la tabla no existe~~ **Resuelto (20/11, PR #41)**: `usuarios.md` §7 ya no apunta a `V13`, sino a editar una migración existente | `docs/reglas/usuarios.md` §7 |
| H6 | ~~V12 siembra motores OCR en cloud, `preservar_formato_pdf = true`, `tiempo_max_revision_minutos = 60` y `version_esquema_bd = 1`~~ **Resuelto (20/11)**: `V15` corrige los cuatro (paddleocr-vl en local, `false`, clave borrada, versión 15) | `V15:141-161` |
| H7 | ~~`vault/Inicio.md` escribe `Investigacion/` y la carpeta es `investigacion/`: en Linux rompe~~ **Ya estaba bien** (minúscula) | `vault/Inicio.md` |
| H8 | ~~`categorias_sensibles` marca `NUSS` como `rgpd_especial`~~ **Resuelto (20/11)**: `V15` lo pone en `false` | `V15:136-139` |
| H9 | ~~**No había stack de backend escrito**: ni lenguaje, ni framework, ni driver, ni dónde se despliega. Solo `reportlab` en el diseño del PDF~~ **Reabierto (20/11)**: con el ETL fuera, [[0014-stack-backend-c-sharp-java-python]] decide entre C#, Java y Python | `README.md`, `docs/architecture/README.md` |

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

0. **Stack** (H9): **reabierto** (20/11): [[0014-stack-backend-c-sharp-java-python]] decide entre C#, Java y Python. @Rubén.
1. **Identidad** (B1): es lo único que sigue abierto. @Rubén ya votó 0009 (SSO + admin local) y 0008 está reabierta; faltan @Kevin y @Alex en 0012. Mientras no se cierre, el alta de usuarios se queda fuera del piloto; no habrá `V13`.
2. **Defectos que piden decisión**: E-33 (`regla_categorias` frente a `reglas_anonimizacion.configuracion`), E-38 (mapa de seudónimos), E-39 (licencia de PyMuPDF), E-44 (retención y acción por defecto en el documento RGPD). Los demás están en el [[Registro de errores]].
3. **Maqueta** (I4, I8): el botón «Exportar PDF» de la revisión sigue activo antes de aprobar, y hay que decidir si la demo va con una o dos personas.

Lo cerrado no se reabre: B3, B5, B6, B7, B8, I1, I2, I3, I9 y H1-H8 se resolvieron entre el 17 y el 20/11 y su fila lo dice.
