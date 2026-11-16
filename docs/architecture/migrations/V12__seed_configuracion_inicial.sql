-- Configuración base del sistema

INSERT INTO configuracion_sistema (clave, valor, descripcion) VALUES
-- Motores OCR disponibles
('motores_ocr_disponibles', 
 '["tesseract", "paddleocr", "azure_document_intelligence", "google_document_ai"]',
 'Motores OCR configurados en el sistema'),

-- Modelos IA para anonimización (NER español jurídico)
('modelos_ia_anonimizacion',
 '["presidio-es", "spacy-es-lg", "custom-ner-juridico-v1", "bert-base-spanish-wwm-cased-ner"]',
 'Modelos NER disponibles para detección de entidades'),

-- Umbrales globales
('umbral_confianza_global', '0.85', 'Confianza mínima para auto-aplicar anonimización sin revisión'),
('umbral_confianza_revision', '0.70', 'Por debajo de esto va directo a revisión humana'),

-- Acciones por defecto
('accion_por_defecto', '"tachado"', 'Acción default: tachado|pseudonimizado|eliminado'),
('preservar_formato_pdf', 'true', 'Mantener layout visual en PDF de salida'),

-- Workflow revisión
('max_intentos_revision', '3', 'Máximo ciclos revisión-edición antes de escalar'),
('tiempo_max_revision_minutos', '60', 'Timeout aviso revisor'),

-- Retención legal
('retencion_auditoria_meses', '120', 'Retención logs auditoría (10 años = 120 meses)'),
('retencion_documentos_meses', '60', 'Retención documentos y versiones (5 años)'),

-- Exportación
('pdf_export_incluir_marcas_agua', 'true', 'Marcar PDF exportado como "ANONIMIZADO - CONFIDENCIAL"'),
('pdf_export_metadatos_limpios', 'true', 'Limpiar metadatos PDF original (autor, fechas, GPS)'),

-- Notificaciones
('notificar_revisor_nuevas_pendientes', 'true', 'Email/Slack a revisor cuando hay cola'),
('notificar_transcriptor_rechazo', 'true', 'Avisar transcriptor si revisor rechaza'),

-- Sistema
('version_esquema_bd', '1', 'Versión actual del esquema (Flyway)'),
('modo_mantenimiento', 'false', 'Activar/desactivar modo mantenimiento');

-- Verificación
-- SELECT clave, valor, descripcion FROM configuracion_sistema ORDER BY clave;