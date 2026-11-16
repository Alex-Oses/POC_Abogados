# Diccionario de Datos - Anonimización iCAT

## Convenciones
- **PK** = Primary Key | **FK** = Foreign Key | **UK** = Unique Key | **NN** = NOT NULL
- Tipos: `uuid` (gen_random_uuid), `timestamptz` (UTC), `jsonb` (flexible), `decimal(p,s)`

---

## usuarios
| Campo | Tipo | Nulos | Clave | Descripción |
|-------|------|-------|-------|-------------|
| id | uuid | NO | PK | Identificador único |
| email | varchar(255) | NO | UK | Email corporativo (login) |
| nombre_completo | varchar(200) | NO | | Nombre + apellidos |
| rol | varchar(50) | NO | | transcriptor / revisor / admin / supervisor |
| activo | boolean | NO | | Baja lógica (no borrado) |
| creado_en | timestamptz | NO | | Alta en sistema |
| actualizado_en | timestamptz | NO | | Última modificación perfil |

---

## categorias_sensibles
| Campo | Tipo | Nulos | Clave | Descripción |
|-------|------|-------|-------|-------------|
| id | uuid | NO | PK | Identificador |
| codigo | varchar(50) | NO | UK | Clave técnica (DNI_NIE, SALUD, MENORES...) |
| nombre | varchar(150) | NO | | Nombre legible UI |
| descripcion | text | SÍ | | Definición funcional |
| regex_patron | varchar(500) | SÍ | | Regex validación post-detección |
| nivel_riesgo | varchar(20) | NO | | alto / medio / bajo |
| rgpd_especial | boolean | NO | | TRUE = Art. 9 RGPD (salud, genéticos, etc.) |
| activa | boolean | NO | | Baja lógica catálogo |

---

## documentos
| Campo | Tipo | Nulos | Clave | Descripción |
|-------|------|-------|-------|-------------|
| id | uuid | NO | PK | Identificador |
| nombre_original | varchar(500) | NO | | Nombre archivo subido |
| hash_sha256 | char(64) | NO | UK | SHA-256 binario (dedup) |
| mime_type | varchar(100) | NO | | application/pdf, image/png, image/jpeg... |
| tamano_bytes | bigint | NO | | Tamaño en bytes |
| ruta_almacenamiento | varchar(1000) | NO | | Ruta S3/MinIO/FS |
| estado | varchar(50) | NO | | pendiente → ocr_procesando → ocr_completado → anonimizando → en_revision → aprobado/rechazado → exportado |
| metadatos_extras | jsonb | NO | | folio, juzgado, fecha_doc, tipo_procedimiento, numero_procedimiento... |
| creado_por | uuid | SÍ | FK→usuarios | Usuario que sube |
| creado_en | timestamptz | NO | | Timestamp subida |
| actualizado_en | timestamptz | NO | | Último cambio estado/metadatos |

---

## versiones_documento
| Campo | Tipo | Nulos | Clave | Descripción |
|-------|------|-------|-------|-------------|
| id | uuid | NO | PK | Identificador versión |
| documento_id | uuid | NO | FK | Documento padre |
| numero_version | int | NO | | 1,2,3... secuencial por documento |
| tipo_version | varchar(30) | NO | | original / ocr_texto / anonimizado_ia / revisado_humano / final_aprobado |
| contenido_texto | text | SÍ | | Texto plano (OCR o resultado) |
| contenido_html | text | SÍ | | Texto con markup entidades para diff UI |
| ruta_pdf | varchar(1000) | SÍ | | PDF renderizado de esta versión |
| motor_ocr | varchar(50) | SÍ | | tesseract / paddleocr / azure / google |
| modelo_ia | varchar(100) | SÍ | | presidio-es / spacy-es-lg / custom-ner-v1 |
| confianza_promedio | decimal(4,3) | SÍ | | Media confianza entidades (0-1) |
| metadatos_proceso | jsonb | NO | | {tiempo_ms, params, warnings, tokens} |
| creado_por | uuid | SÍ | FK→usuarios | NULL si automático |
| creado_en | timestamptz | NO | | Timestamp creación versión |

---

## reglas_anonimizacion
| Campo | Tipo | Nulos | Clave | Descripción |
|-------|------|-------|-------|-------------|
| id | uuid | NO | PK | Identificador |
| codigo | varchar(50) | NO | UK | RGPD_ES / LOPD / CAT_CIVIL / PENAL_MENORES |
| nombre | varchar(200) | NO | | Nombre legible |
| descripcion | text | SÍ | | Qué cubre la regla |
| configuracion | jsonb | NO | | Ver estructura abajo |
| version | int | NO | | Versionado regla |
| activa | boolean | NO | | Vigente |
| creado_por | uuid | SÍ | FK→usuarios | Admin que crea |
| creado_en | timestamptz | NO | | |
| actualizado_en | timestamptz | NO | | |

**Estructura `configuracion` (JSONB):**
```json
{
  "entidades_obligatorias": ["DNI_NIE", "NOMBRE_PERSONA", "DIRECCION", "TELEFONO", "EMAIL", "IBAN", "NUSS"],
  "entidades_opcionales": ["MATRICULA", "IP", "FECHA_NACIMIENTO", "REF_CATASTRAL"],
  "accion_por_defecto": "tachado",
  "acciones_por_categoria": {"SALUD": "pseudonimizado", "MENORES": "eliminado"},
  "excepciones": {"NOMBRE_PERSONA": ["juez", "fiscal", "notario", "letrado_admin"]},
  "umbral_confianza": 0.85,
  "preservar_formato": true,
  "pseudonimizado_prefijo": "[ENTIDAD_",
  "pseudonimizado_sufijo": "]"
}