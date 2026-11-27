# 0019 · Entrada de PDF por SharePoint

- **Estado**: Aceptada (2026-11-27, @Rubén)
- **Fecha**: 2026-11-26
- **Autor**: @ia-claude-alex

## Contexto

Nos piden que los PDF dejados en una carpeta de SharePoint se suban solos a la app y empiecen a transcribirse, y que conste quién los subió: la carpeta lleva el nombre de la persona.

## Decisión

- El backend sondea Microsoft Graph cada `SHAREPOINT_SONDEO_SEG` (60 s) con una app de Entra ID (client credentials). Sin `SHAREPOINT_*` en `.env` no se activa.
- Estructura: `<SHAREPOINT_CARPETA>/<Nombre Persona>/fichero.pdf`. Cada PDF entra por `registrar_subida` (mismas validaciones que la web) con `subido_por = <Nombre Persona>` y `origen = sharepoint`.
- Si el nombre coincide con un usuario activo (`nombre` o `nombre apellidos`), el documento es suyo; si no, queda a nombre del admin y lo ven revisores y admin.
- Tras subirlo, el fichero se mueve a `<persona>/Procesados` (o a `Rechazados` si la app no lo acepta). Así nunca se sube dos veces y no hace falta guardar estado.
- «Subido por» se guarda en `documentos.metadatos_extras.subido_por`: **sin cambios de esquema**.
- Sondeo y no webhooks: el servidor no necesita URL pública ni renovar suscripciones.

## Consecuencias

- Hace falta registrar la app en Entra ID con permiso de aplicación `Files.ReadWrite.All` (o `Sites.Selected` sobre el sitio) y sacar el `drive_id` de la biblioteca.
- Hasta 60 s de retraso entre dejar el PDF y que aparezca en la bandeja.
- Un solo proceso backend (igual que la cola, [[0020-cola-ocr-en-segundo-plano]]).
