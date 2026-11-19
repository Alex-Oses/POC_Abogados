# 2026-11-18 · @ia-opencode-alex

## Hecho

- Repaso de lo mergeado en `main` desde el 16/11 (PR #22 a #29, de @Rubén y @maga369), sin cambios de código míos.
- **Modelo de datos**: [[0010-modelo-de-datos]] reescrita para @Marina y [[Modelo de datos]] con su modelo comparado. [[0011-ajustes-al-modelo-de-marina]] **aceptada** el 17/11: se quitan 4 columnas, `revisor_id` pasa a `asignado_a`, entra `paginas_documento` y no hay tabla de seudónimos.
- **Migraciones**: `V14` (`bloques_layout`, `paginas_documento`) y `V15` (flujo de revisión y export) escritas, con `triggers.sql` y `views.sql` alineados. Sin ejecutar contra PostgreSQL 16 (Docker no arranca en la máquina de @maga369).
- **Identidad y roles**: [[0012-identidad-y-roles]] en Propuesta (SSO, tres roles sin supervisor, columna `usuarios.roles`, sin `tokens_usuario`). Toca [[0005-reglas-usuarios-y-aprobacion]] y [[0009-identidad]]. `V13` espera a que @Marina acepte.
- **Enfoque técnico del backend**: [[Enfoque tecnico]] (propuesta).
- **Reglas**: nuevo `docs/reglas/reglas-de-negocio.md` con todas las reglas en un fichero y `docs/pendientes.md` con lo que falta decidir. Retiradas U-07, A-07, A-20 y U-10 a U-15; A-15 en pausa; A-24 (doble transcripción) en propuesta.
- **Contrato**: `docs/api/endpoints.md` sin rutas de invitación ni de reset de contraseña; entran `GET /auth/sso/login` y `/callback` como propuesta.

## Siguiente

- Votar [[0009-identidad]] y [[0012-identidad-y-roles]] (me toca como @Alex).
- Decidir A-24 (doble transcripción) con @Rubén.
- Pasar la [[Maqueta]] a Figma y decidir el caso del viernes 27/11.
- Ajustar Presidio (modelo `lg`, palabras a ignorar, direcciones y matrícula).

## Bloqueos / preguntas

- B8 (dueño del hash del PDF) sigue sin votar; la recomendación de 0011 es que sea de la versión.
- Sesión: delegarla en el ICAT o crear `sesiones_usuario`.
- [[Tablero]] tiene la línea «Enfoque técnico del backend» duplicada en «Hecho» y [[Modelo de datos]] aún cita U-13 (retirada); no los he tocado.
