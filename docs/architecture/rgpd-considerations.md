# Consideraciones RGPD / LOPD en el Modelo de Datos

> Modelo de referencia: la v0.3 del 24/11/2026 (14 tablas), que la edición actual de `V15` ya cubre en tablas. Las diferencias de columnas están en el [README](README.md) y en el [diccionario](data-dictionary.md) (E-53).

## 1. Minimización de Datos (Art. 5.1.c RGPD)
- **No se almacenan** datos sensibles en `documentos.metadatos_extras` ni `versiones_documento.metadatos_proceso`.
- `anotaciones_entidad.texto_original` contiene el dato sensible **solo mientras dura el proceso**. El PDF final se reconstruye con las sustituciones, sin capa oculta ni texto de origen (0007); la versión `final_aprobado` conserva el original como fuente y solo lo ve revisor o admin.
- `sesiones_usuario.token_hash` guarda el SHA-256 del token opaco, nunca el token.
- `regla_categorias.configuracion` guarda acción, umbral y excepciones, no datos de las personas.
- `auditoria.detalle` registra **acciones**, no contenido sensible (`hash_anterior` garantiza integridad sin replicar datos).

## 2. Derecho al Olvido / Supresión (Art. 17 RGPD)
| Tabla | Estrategia |
|-------|------------|
| `documentos` | Borrado lógico (`eliminado_en`); el borrado físico del archivo y su plazo quedan por decidir (U-08, E-44) |
| `paginas_documento`, `bloques_layout`, `versiones_documento` | Se borran con el documento o la versión |
| `anotaciones_entidad` | Contiene el dato sensible → **borrado obligatorio** cuando se decida la retención (E-44); mientras tanto se conserva con la versión (A-18) |
| `revisiones` | Se borra con la versión; el histórico de quién revisó queda en `auditoria` |
| `usuarios_roles` | Se borra con la cuenta; el alta del rol queda en `auditoria` |
| `sesiones_usuario` | Se borra con la cuenta; las revocadas y caducadas se purgan a los 30 días |
| `regla_categorias` | Sin dato personal: se elimina con la regla o la categoría |
| `auditoria` | **NO se borra** (base legal: obligación legal Art. 6.1.c + interés público Art. 6.1.e). Se pseudonimiza `usuario_id` a `NULL` tras 120 meses. |

## 3. Limitación del Tratamiento (Art. 18 RGPD)
- `usuarios.estado` (`activo`, `bloqueado`, `baja`), `motivo_baja` y `eliminado_en`; `categorias_sensibles.activa` y `reglas_anonimizacion.activa` → baja lógica, no borrado.
- `sesiones_usuario.revocado_en` corta el tratamiento en cuanto se revoca la sesión.
- `documentos.estado='rechazado'` congela el tratamiento; `cerrado_en` (A-19) congela el aprobado.

## 4. Responsabilidad Proactiva / Accountability (Art. 5.2 + 24 RGPD)
- `auditoria` con **hash encadenado** (`hash_anterior`) → prueba de inalterabilidad ante la autoridad de control.
- `anotaciones_entidad` guarda **motor, confianza, decisión humana** → explicabilidad de cada anonimización.
- `revisiones.numero_intento`, `comentario_general` y `finalizado_en` → evidencia del proceso «humano en el bucle»; `actualizado_en` es el `If-Match` de A-23.
- `usuarios_roles.otorgado_por` y `otorgado_en` → quién concedió cada permiso y cuándo (los propone la v0.3; el SQL actual solo guarda el par usuario/rol, E-53).

## 5. Seguridad del Tratamiento (Art. 32 RGPD)
- `hash_sha256` en `documentos` → detección de duplicados sin comparar contenido.
- `clave_cifrado` guarda solo el **id de la KEK**; el material de la clave vive fuera de la BD.
- `ruta_almacenamiento` apunta a storage **cifrado en reposo** (S3 SSE-KMS / MinIO SSE).
- `token_hash` en `sesiones_usuario` → tokens opacos revocables sin guardar el secreto.
- `ip_origen`, `user_agent` en `auditoria` y en `sesiones_usuario` → detección de accesos anómalos.

## 6. Registro de Actividades de Tratamiento (Art. 30 RGPD)
El modelo cubre los requisitos del ROPA:
- **Finalidad**: anonimización documentos judiciales (interés público + obligación legal).
- **Categorías interesados**: partes, testigos, peritos, menores, víctimas (vía `categorias_sensibles.rgpd_especial`).
- **Categorías datos**: identificativos, financieros, salud, condenas, vulnerables (mapeados en catálogo).
- **Destinatarios**: personal interno, con los roles de `usuarios_roles` (`admin`, `transcriptor`, `revisor`), sin cesiones externas.
- **Transferencias internacionales**: ninguna (storage UE, modelos IA on-premise/self-hosted).
- **Plazos supresión**: 60 meses para documentos y 120 para auditoría; las claves concretas viven en `configuracion_sistema` (`V12` corregido por `V15`), no en la v0.3.

## 7. Evaluación de Impacto (EIPD - Art. 35 RGPD)
**Requerida SÍ** porque:
- Tratamiento masivo de categorías especiales (salud, menores, condenas).
- Uso de IA (NER) para decisiones automatizadas que afectan derechos.
- Vigilancia sistemática (auditoría completa).

El modelo facilita la EIPD al tener **trazabilidad granular por entidad** (`anotaciones_entidad`).

## 8. Diseño Privacy by Design (Art. 25 RGPD)
- **Por defecto**: `censurar` (acción por defecto desde V15), más seguro que pseudonimizar.
- **Umbral por par regla/categoría**: `regla_categorias.configuracion` (`umbral`, `accion`, `excepciones`).
- **Revisión humana obligatoria**: `pendiente_revision` cuando la confianza está por debajo del umbral.
- **Exportación limpia**: PDF reconstruido sin capa oculta; el hash de la versión va en `versiones_documento.metadatos_proceso` (B8 cerrado el 19/11; la v0.3 todavía lo sitúa en `documentos.hash_export`).

---

## Checklist Cumplimiento para Desarrollo

- [ ] Cifrado en tránsito (TLS 1.3) y reposo (AES-256) en storage.
- [ ] Logs de acceso a BD (pg_audit) separados de `auditoria` aplicativa.
- [ ] Backup cifrado + test de restauración trimestral.
- [ ] Procedimiento supresión de `anotaciones_entidad` < 30 días tras la exportación final.
- [ ] Revocar `sesiones_usuario` al cambiar roles, bloquear o dar de baja la cuenta.
- [ ] Verificar que `bloque_id` pertenece a la `version_id` de la anotación (FK compuesta).
- [ ] DPIA documentada y firmada por DPO antes de puesta en producción.
- [ ] Contrato encargado tratamiento (Art. 28) si storage/OCR/IA son proveedores cloud.