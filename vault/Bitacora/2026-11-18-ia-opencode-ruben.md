# 2026-11-18 · @ia-opencode-ruben

## Hecho

- [[0012-identidad-y-roles]] (Propuesta, @Rubén): SSO sin gestión de cuentas, tres roles (sin supervisor) y varios roles por usuario. Incluye el análisis de qué cambia en el modelo aceptado en [[0011-ajustes-al-modelo-de-marina]]: `usuarios.rol` sale y **entra una columna `roles`, sin tabla**; `sso_subject` y `estado` también; `tokens_usuario` no se crea. Todo cabe en `V13`, que aún no existe, así que no hay datos que migrar.
- [[Enfoque tecnico]] §5 reescrito: SSO como única entrada, admin local solo de desarrollo, roles múltiples y visto bueno por un revisor distinto del que cerró. §10 y §11 alineados.
- [[0005-reglas-usuarios-y-aprobacion]]: roles múltiples, alta por SSO, asignación por cualquier revisor y doble firma de otro revisor.
- [[0009-identidad]]: la opción 3 pasa de «admin de emergencia» a «admin de desarrollo»; `tokens_usuario` deja de usarse en producción.
- `docs/reglas/usuarios.md`: U-01 (roles múltiples), U-02, U-03, U-05 (alta por SSO), U-07, U-09, U-19, matriz de capacidades y §7.
- `docs/reglas/aprobacion.md`: A-06, A-07, A-08, A-14, A-15, A-19 y A-20 pasan de supervisor a revisor; el `sign-off` exige otro revisor.
- `docs/api/endpoints.md`: bloque de roles, cuatro rutas (`assign`, `sign-off`, `audit`), payloads `rol` → `roles` y textos; las rutas de contraseña quedan marcadas como camino del admin de desarrollo.
- [[Coherencia]]: B2 e I4 actualizados al modelo de roles nuevo.
- [[Tablero]]: tareas de 0012, `V13` y el callback SSO; pregunta a @Marina en «Preguntas abiertas».
- [`docs/reglas/reglas-de-negocio.md`](../../docs/reglas/reglas-de-negocio.md): las reglas numeradas en un solo fichero para leerlas seguidas y editarlas a mano, con el estado de cada una y una sección «Cambios pedidos».
- Revisión de @Rubén aplicada a las reglas: U-03 solo limita al transcriptor puro; U-07 (72 h), A-07 (nadie revisa lo suyo) y A-20 (plazos) se retiran; A-06 pasa a cola libre; A-15 (doble firma) queda en pausa; A-04 no cambia y la idea de transcribir dos veces entra como A-24 (propuesta).
- U-10 a U-15 retiradas (18/11) y sustituidas por **U-21**: la credencial del admin de desarrollo se siembra por variable de entorno, no vive en el repo y no se despliega en producción. El admin local sigue funcionando igual, sin reglamento propio.
- Contrato alineado con lo anterior: fuera `fecha_limite` (A-20) y los `403` por «nadie revisa lo suyo» (A-07); fuera el rol `S` de la tabla de rutas; las rutas de contraseña quedan como bloque de desarrollo; entran `GET /auth/sso/login` y `GET /auth/sso/callback` marcadas como propuesta.
- `.docx` de `local/` regenerados desde el markdown: `endpoints.docx`, `usuarios.docx`, `aprobaciones.docx` y, nuevo, `reglas-negocio.docx` con la lista única.
- Análisis del modelo de @Marina a petición de @Rubén: con las reglas de hoy **no hace falta ninguna tabla nueva para los roles** (columna `roles TEXT[]` con su `CHECK` e índice GIN). La única tabla candidata es `sesiones_usuario`, y solo si no se delega la sesión en el ICAT. `tokens_usuario` no se crea. Detalle y SQL en [[0012-identidad-y-roles]].
- Propagado a la bóveda: [[0012-identidad-y-roles]], [[0005-reglas-usuarios-y-aprobacion]], [[0009-identidad]], [[0011-ajustes-al-modelo-de-marina]] (anexo con A-20 retirada y A-15 en pausa), [[Enfoque tecnico]] §5 y §11, [[Coherencia]] (B1 y B4), [[Tablero]] y `docs/pendientes.md`.
- Cerrado el issue #24 (lo que bloqueaba empezar el backend): `V14` y `V15` ya están escritas y el seguimiento vive en el tablero, 0011 y 0012.

## Siguiente

- Que @Marina acepte `roles`, `estado`, `sso_subject` y el cambio de `triggers.sql`/`views.sql`; después escribe `V13`.
- Decidir la sesión: delegarla en el ICAT (cero tablas, se retiran U-16 a U-20) o `sesiones_usuario`.
- Votos de @Kevin y @Alex a [[0009-identidad]] y [[0012-identidad-y-roles]].
- Pedir al ICAT el registro OIDC: es la única dependencia de 1-2 semanas que no se puede adelantar con código.
- B8 (dueño del hash) y `GET /documents/{id}/pages` siguen en el tablero.

## Bloqueos / preguntas

- @Marina: el cambio de roles toca su modelo aceptado y el `trigger` de validación de revisor, que consulta `usuarios.rol`.
- @Rubén: decidir si la doble firma con tres roles se queda como «otro revisor» (propuesto) o se relaja para la demo.
- El diagrama de @Marina y `data-dictionary.md` siguen con `rol` único hasta que ella acepte 0012.
- `vault/Proyecto/Modelo de datos.md` sigue etiquetando `password_cambiado_en` como U-13, retirada; es su fichero y no lo toco.
