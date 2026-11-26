# 2026-11-26 · @ia-opencode-ruben

## Hecho

- Creado el backend Python en `backend/` con la estructura aceptada: FastAPI, `psycopg` 3, SQL directo en `.sql` y sin ORM. Una petición, una transacción; `services/` separado de `api/`.
- Primera rebanada vertical: login local, `/user/me`, logout, cambio de contraseña, listado/edición de usuarios y revocación de sesiones.
- Sesiones opacas con tope de 3, 1 h deslizante y techo de 12 h; cambiar roles o estado revoca las sesiones.
- Auditoría con cadena de hash en la misma transacción, bajo advisory lock.
- El admin de desarrollo (U-21) se siembra por entorno y lleva **los tres roles** (transcriptor, revisor y admin). El arranque lo deja activo. No hay rutas SSO: queda en pausa a propósito.
- `ruff` limpio y `pytest` con 7 pruebas en verde; las 4 de BD se saltan por no haber PostgreSQL en este equipo. Arranque real comprobado: sin BD, `/health` devuelve `503`.
- Movida la investigación de reconstrucción de PDF a `investigacion/reconstruccion_pdf/` y a su propio PR, separada del backend.
- Actualizados `docs/api/endpoints.md`, `docs/reglas/usuarios.md`, `docs/pendientes.md`, [[Enfoque tecnico]] y el tablero.

## Siguiente

- Aplicar `V1`..`V15` en PostgreSQL 16 desde cero y ejecutar las 4 pruebas de integración.
- Elegir la siguiente rebanada del backend: documentos/OCR o reglas y configuración.
- Retomar el SSO cuando el ICAT registre la aplicación OIDC.

## Bloqueos / preguntas

- Sin Docker ni `psql` no se ha validado nada contra la base de datos real.
- El OCR síncrono o por página (I5) sigue sin dueño y bloquea subida y transformación.
- La frontera con el ETL (@Yaser) sigue abierta: quién escribe `bloques_layout` y `anotaciones_entidad`.
