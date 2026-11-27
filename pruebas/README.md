# Documentos de prueba

Todos ficticios (nunca datos reales: AGENTS.md). Se regeneran con
`backend/.venv/bin/python scripts/generar_pruebas.py`.

| Fichero | Para probar |
|---|---|
| 01–05 | Un documento de cada tipo: DNI, nómina, padrón, IRPF, notificación del juzgado |
| 06_contrato_datos_personales | Anonimización: nombres, DNI, IBAN, teléfono y correo |
| 07_solicitud_catalan | Justicia gratuita en catalán (Nom, Ingressos) |
| 08_expediente_jg_completo | Justicia gratuita completa (17 páginas, 12 nóminas) |
| 09_expediente_jg_incompleto | Justicia gratuita a la que le falta documentación |
| 10_pagina_ilegible | Semáforo: página casi blanca, se marca ilegible |
| 11_largo_20_paginas | Cola, progreso y miniaturas con muchas páginas |
| 12–14 | Escaneos sin capa de texto: limpio, torcido con ruido y degradado |
| 15_padron_foto.jpg, 16_dni.png | Subida de imágenes |
| 17_no_es_pdf | Debe rechazarse (415) |

Para volver a subir uno ya subido (la app avisa de duplicado), haz una copia con otro contenido o súbelo con otro usuario.
