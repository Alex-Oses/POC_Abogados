# 2026-11-19 · @ia-opencode-ruben

## Hecho

- Aceptadas por @Rubén (19/11): 0002 (PostgreSQL + Flyway), 0005 (reglas de usuarios y aprobación), 0006 (Presidio local) y 0007 (PDF final).
- Confirmación de @Rubén (19/11): stack Python + FastAPI (0008) e identidad SSO con admin local solo de desarrollo (0009). Ambas siguen **Propuesta**: faltan @Marina, @Kevin y @Alex.
- Revisión de coherencia de `docs/api/endpoints.md`, `vault/Proyecto/API.md`, `vault/Proyecto/Enfoque tecnico.md`, `docs/reglas/usuarios.md` y `docs/reglas/aprobacion.md` contra las reglas U/A, el modelo de @Marina y `V14`/`V15`.
- Contrato: `If-Match` usa `actualizado_en` (columna real de `revisiones`, A-23), no `updated_at`; el cierre de revisión es el único que lo exige.
- Contrato: `DELETE /documents/{id}` pasa el documento a `eliminado` y rellena `eliminado_en`; `GET /documents` excluye los eliminados. Se añade `eliminado` a la máquina de estados.
- Contrato: la subida escribe `paginas_documento` (V14) además de `documentos`, versiones y `bloques_layout`.
- Contrato: `pendientes=true` se define como `decision_revisor IS NULL` (A-09) y `PATCH /annotations/{id}` devuelve `409` si la revisión no está `en_proceso` (A-11).
- Contrato y reglas: `pendiente_visto_bueno` queda marcado como en pausa con A-15.
- [[aprobacion]] §10 deja de decir «lo que falta en el esquema»: las columnas de A-04/A-05/A-15/A-19/A-20/A-23 ya están en `V15`; solo el hash del PDF (B8) sigue pendiente.
- [[usuarios]] §7: `password_cambiado_en` no se crea (0012) y se añade `sesiones_usuario.expira_en`, que U-16 y U-18 necesitan. El callback SSO ya está en el contrato como propuesta.
- [[Enfoque tecnico]]: 38 rutas (no 40), admin de desarrollo sembrado por variable de entorno (U-21), `If-Match` solo en el cierre de revisión y sin invitación en el bloque de autenticación.
- [[API]]: 38 rutas y bloques de autenticación/usuarios ajustados al SSO; el visto bueno se marca en pausa.
- [[0012-identidad-y-roles]]: `sesiones_usuario` gana `expira_en` en el SQL de `V13`; sin ella no se puede implementar U-18 (1 h con renovación y 12 h máximo).
- [[reglas-de-negocio]]: A-23 usa `actualizado_en` y U-21 ya no menciona el reset de contraseña, retirado con U-10 a U-15.

## Siguiente

- B8 (dueño del hash) y `GET /documents/{id}/pages` siguen abiertos: no se tocan porque son decisión y ruta nuevas, no incoherencias de lo ya escrito.
- Que @Marina revise el `expira_en` añadido a `V13` y acepte 0012 antes de escribir la migración.

## Bloqueos / preguntas

- `docs/architecture/data-dictionary.md` sigue con `rol` y `activo`; no se toca hasta que @Marina acepte 0012 y escriba `V13`.
- A-19 dice que la reapertura rellena `cerrado_en`, pero `V15` y el contrato lo escriben en el export. La reapertura de un aprobado sigue abierta en [[Coherencia]] B7; no se cambia la regla por la puerta de atrás.
