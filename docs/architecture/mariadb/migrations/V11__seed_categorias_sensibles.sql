-- MariaDB 11.4+ · equivalente de migrations/V11__seed_categorias_sensibles.sql
-- Las barras de las regex se duplican: en MariaDB '\d' se convierte en 'd' (escape no reconocido).

INSERT INTO categorias_sensibles (codigo, nombre, descripcion, regex_patron, nivel_riesgo, rgpd_especial, activa) VALUES
-- Identificadores directos (alto riesgo)
('DNI_NIE', 'DNI / NIE / Pasaporte', 'Documento nacional de identidad, NIE o pasaporte español', '[XYZ]?\\d{7,8}[A-Z]', 'alto', false, true),
('NOMBRE_PERSONA', 'Nombre de persona física', 'Nombre y apellidos de persona física', NULL, 'alto', false, true),
('TELEFONO', 'Teléfono fijo o móvil', 'Número de teléfono español (fijo 9xx / móvil 6xx/7xx)', '(\\+34|0034)?[679]\\d{8}', 'medio', false, true),
('EMAIL', 'Correo electrónico', 'Dirección de email personal o profesional', '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}', 'medio', false, true),
('DIRECCION', 'Dirección postal completa', 'Calle, número, piso, puerta, código postal, localidad', NULL, 'alto', false, true),
('FECHA_NACIMIENTO', 'Fecha de nacimiento', 'Fecha nacimiento persona física', '\\d{2}/\\d{2}/\\d{4}', 'medio', false, true),
('SEXO', 'Sexo / Género', 'Dato de sexo o identidad de género', NULL, 'medio', true, true),

-- Identificadores financieros / administrativos (alto riesgo)
('IBAN', 'Cuenta bancaria IBAN', 'Código IBAN español (ES + 22 dígitos)', 'ES\\d{22}', 'alto', false, true),
('NUSS', 'Número Seguridad Social', 'Número de afiliación a la Seguridad Social', '\\d{2}/\\d{8}/\\d{2}', 'alto', true, true),
('NUM_COLEGIADO', 'Número de colegiado', 'Identificador profesional (abogado, procurador, perito)', '\\d{4,6}', 'medio', false, true),

-- Identificadores de bienes / vehículos
('MATRICULA', 'Matrícula de vehículo', 'Matrícula española (4 dígitos + 3 letras)', '\\d{4}[BCDFGHJKLMNPRSTVWXYZ]{3}', 'medio', false, true),
('REF_CATASTRAL', 'Referencia catastral', 'Referencia catastral inmueble (20 caracteres)', '[0-9A-Z]{20}', 'medio', false, true),

-- Digitales / Técnicos
('IP', 'Dirección IP', 'IPv4 o IPv6', '(\\d{1,3}\\.){3}\\d{1,3}|([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}', 'bajo', false, true),
('DATOS_BIOMETRICOS', 'Datos biométricos', 'Huella, reconocimiento facial, iris, voz', NULL, 'alto', true, true),
('DATOS_GENETICOS', 'Datos genéticos', 'ADN, pruebas genéticas, historial familiar', NULL, 'alto', true, true),

-- Categorías especiales RGPD Art. 9 (alto riesgo + especial)
('SALUD', 'Datos de salud', 'Historial médico, diagnósticos, recetas, partes de baja, discapacidad', NULL, 'alto', true, true),
('ORIGEN_RACIAL', 'Origen racial o étnico', 'Origen racial, étnico, nacionalidad', NULL, 'alto', true, true),
('RELIGION', 'Creencias religiosas', 'Religión, creencias filosóficas', NULL, 'alto', true, true),
('SINDICATO', 'Afiliación sindical', 'Pertenencia a sindicato', NULL, 'alto', true, true),
('ORIENTACION_SEXUAL', 'Orientación sexual', 'Orientación sexual o vida sexual', NULL, 'alto', true, true),
('CONDENAS_PENALES', 'Condenas e infracciones penales', 'Antecedentes penales, medidas de seguridad', NULL, 'alto', true, true),

-- Colectivos vulnerables
('MENORES', 'Datos de menores de edad', 'Cualquier dato identificativo de menor de 18 años', NULL, 'alto', true, true),
('PERSONAS_DISCAPACIDAD', 'Personas con discapacidad', 'Datos que revelen discapacidad física/psíquica', NULL, 'alto', true, true),
('VICTIMAS_VIOLENCIA', 'Víctimas violencia de género/doméstica', 'Datos de víctimas protegidas (Ley Orgánica 1/2004)', NULL, 'alto', true, true);
