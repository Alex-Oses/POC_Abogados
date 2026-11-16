# Consideraciones RGPD / LOPD en el Modelo de Datos

## 1. Minimización de Datos (Art. 5.1.c RGPD)
- **No se almacenan** datos sensibles en `documentos.metadatos_extras` ni `versiones_documento.metadatos_proceso`.
- `anotaciones_entidad.texto_original` contiene el dato sensible **solo mientras dura el proceso**; al exportar PDF final, la versión `final_aprobado` ya no lo incluye.
- `auditoria.detalle` registra **acciones**, no contenido sensible (hash_anterior garantiza integridad sin replicar datos).

## 2. Derecho al Olvido / Supresión (Art. 17 RGPD)
| Tabla | Estrategia |
|-------|------------|
| `documentos` | Soft delete (`estado='eliminado'`) + borrado físico archivo storage tras 30 días |
| `versiones_documento` | Cascade delete al borrar documento |
| `anotaciones_entidad` | Cascade delete (contiene dato sensible → **borrado obligatorio**) |
| `auditoria` | **NO se borra** (base legal: obligación legal Art. 6.1.c + interés público Art. 6.1.e). Se pseudonimiza `usuario_id` a `NULL` tras 10 años. |

## 3. Limitación del Tratamiento (Art. 18 RGPD)
- Campo `activo` en `usuarios`, `categorias_sensibles`, `reglas_anonimizacion` → baja lógica, no borrado.
- `documentos.estado='rechazado'` congela el tratamiento hasta decisión.

## 4. Responsabilidad Proactiva / Accountability (Art. 5.2 + 24 RGPD)
- `auditoria` con **hash encadenado** → prueba inalterabilidad ante autoridad de control.
- `anotaciones_entidad` guarda **motor, confianza, decisión humana** → explicabilidad de cada anonimización.
- `revisiones.numero_intento` → evidencia de proceso "humano en el bucle".

## 5. Seguridad del Tratamiento (Art. 32 RGPD)
- `hash_sha256` en `documentos` → detección duplicados sin comparar contenido.
- `ruta_almacenamiento` apunta a storage **cifrado en reposo** (S3 SSE-KMS / MinIO SSE).
- `ip_origen`, `user_agent` en `auditoria` → detección accesos anómalos.

## 6. Registro de Actividades de Tratamiento (Art. 30 RGPD)
El modelo cubre los requisitos del ROPA:
- **Finalidad**: anonimización documentos judiciales (interés público + obligación legal).
- **Categorías interesados**: partes, testigos, peritos, menores, víctimas (vía `categorias_sensibles.rgpd_especial`).
- **Categorías datos**: identificativos, financieros, salud, condenas, vulnerables (mapeados en catálogo).
- **Destinatarios**: personal interno (roles `transcriptor`, `revisor`), sin cesiones externas.
- **Transferencias internacionales**: ninguna (storage UE, modelos IA on-premise/self-hosted).
- **Plazos supresión**: `configuracion_sistema.retencion_documentos_meses=60`, `retencion_auditoria_meses=120`.

## 7. Evaluación de Impacto (EIPD - Art. 35 RGPD)
**Requerida SÍ** porque:
- Tratamiento masivo de categorías especiales (salud, menores, condenas).
- Uso de IA (NER) para decisiones automatizadas que afectan derechos.
- Vigilancia sistemática (auditoría completa).

El modelo facilita la EIPD al tener **trazabilidad granular por entidad** (`anotaciones_entidad`).

## 8. Diseño Privacy by Design (Art. 25 RGPD)
- **Por defecto**: `accion_por_defecto="tachado"` (más seguro que pseudonimizar).
- **Umbral alto**: `umbral_confianza_global=0.85` → menos falsos negativos.
- **Revisión humana obligatoria**: `pendiente_revision` estado por defecto en entidades < umbral.
- **Exportación limpia**: `pdf_export_metadatos_limpios=true`, marca agua "ANONIMIZADO".

---

## Checklist Cumplimiento para Desarrollo

- [ ] Cifrado en tránsito (TLS 1.3) y reposo (AES-256) en storage.
- [ ] Logs de acceso a BD (pg_audit) separados de `auditoria` aplicativa.
- [ ] Backup cifrado + test de restauración trimestral.
- [ ] Procedimiento supresión `anotaciones_entidad` < 30 días tras exportación final.
- [ ] DPIA documentada y firmada por DPO antes de puesta en producción.
- [ ] Contrato encargado tratamiento (Art. 28) si storage/OCR/IA son proveedores cloud.