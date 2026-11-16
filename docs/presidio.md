# Anonimización local con Presidio · Documentación y rendimiento

| | |
|---|---|
| Prueba reproducible | `investigacion/presidio/benchmark.py` |
| Resultados | `investigacion/presidio/resultados/resultados.json` |
| Primera prueba guiada | `investigacion/presidio/prueba_es.py` |
| Entorno | Windows 11, Python 3.14, Presidio 2.2.x, spaCy 3.8, CPU (sin GPU) |
| Fecha | Noviembre de 2026 |

## 1. Qué se ha investigado

Antes de publicar o compartir un documento, hay que localizar y tapar los datos personales que contiene (nombres, DNI, direcciones…). La propuesta exige que eso ocurra **sin que el documento salga del servidor del Colegio**.

Esta investigación responde a tres preguntas:

1. ¿Puede Presidio, en local y en castellano y catalán, encontrar los datos personales que aparecen en un documento judicial?
2. ¿Cuánto acierta, cuánto se equivoca y qué hay que ajustar?
3. ¿Cuánto tarda y cuánta memoria necesita?

## 2. Qué es Presidio

[Presidio](https://presidio.dataprivacystack.org/) es una biblioteca de Microsoft, de código abierto y en Python, con dos piezas independientes:

- **Analyzer**: encuentra los datos personales. Combina dos métodos:
  - **Patrones con validación** para los identificadores: DNI, NIE e IBAN no solo se reconocen por su forma, sino que se comprueba su letra o dígito de control.
  - **Modelo de lenguaje (spaCy)** para nombres de persona y lugares, que no tienen una forma fija.
- **Anonymizer**: transforma lo encontrado. Ofrece censurar, reemplazar por etiqueta, enmascarar, cifrar (y descifrar después), sustituir por hash y aplicar una función propia.

Todo se ejecuta en el equipo: no llama a ningún servicio externo y no necesita GPU.

## 3. Qué detecta ya

| Necesidad de la propuesta | Entidad de Presidio | Cómo lo detecta |
|---|---|---|
| DNI | `ES_NIF` | Patrón + letra de control |
| NIE | `ES_NIE` | Patrón + letra de control |
| Pasaporte | `ES_PASSPORT` | Patrón |
| IBAN | `IBAN_CODE` | Patrón + dígito de control |
| Correo electrónico | `EMAIL_ADDRESS` | Patrón + validación |
| Teléfono | `PHONE_NUMBER` | Patrón, con la región España |
| Nombres de personas | `PERSON` | Modelo spaCy |
| Lugares | `LOCATION` | Modelo spaCy |

Lo que la propuesta pide y Presidio **no trae** de serie, y hemos añadido en la configuración «mejorada»:

- **Referencia catastral**: patrón `7 dígitos + 2 letras + 4 dígitos + letra + 4 dígitos + 2 letras`.
- **Matrícula de vehículo**: 4 dígitos y 3 consonantes, con o sin espacio o guion.
- **Dirección completa**: calle, número, piso y código postal. El modelo solo reconoce el nombre de la vía y la ciudad, no el número ni el código postal.
- **Teléfonos con prefijo** (`+34`) y con puntos.
- **DNI con puntos y guion** (`16.769.640-H`).
- **Nombres en mayúsculas** y **nombres catalanes con «i»**: el modelo apenas reconoce unos y corta los otros. Se normalizan antes de leerlos, sin cambiar sus posiciones.
- **Personas jurídicas**: no se anonimizan, como indica el CENDOJ, aunque el modelo las detecte.

## 4. Cómo funciona la anonimización

Dos decisiones que conviene entender antes de mirar resultados:

**Detección y decisión son cosas distintas.** Presidio propone qué tapar; la persona revisora decide en la pantalla de anonimización (ver la [maqueta](maqueta.md)). El sistema nunca exporta sin confirmación.

**Tapar la imagen exige coordenadas.** Para borrar un dato de la imagen del PDF hay que saber dónde está. El OCR que hemos elegido (PaddleOCR-VL por Ollama) devuelve **solo texto, sin coordenadas**. Por eso, para el POC, la exportación genera un PDF nuevo a partir del texto anonimizado: es lo más simple y no deja nada en la imagen. Tapar la imagen original requeriría un segundo OCR solo para las cajas. Está como pregunta abierta al backend.

## 5. Cómo se ha medido

La prueba genera **150 sentencias ficticias** por idioma (unas 1.700 letras cada una, más o menos una página) con los datos personales **marcados de antemano**: nombres, DNI, NIE, direcciones, teléfonos, correos, IBAN, matrículas y referencias catastrales, **más empresas que no deben taparse**. Sobre ese corpus se pasan tres configuraciones:

| Configuración | Qué incluye |
|---|---|
| **base** | Presidio tal como viene: solo modelos y reconocedores de serie |
| **ajustada** | Se añaden patrones propios (catastral, matrícula, dirección, teléfono) y una lista de palabras a ignorar |
| **mejorada** | Además, normaliza nombres en mayúsculas y con «i», descarta municipios e instituciones que el modelo confunde con lugares, y no anonimiza empresas |

Se mide:

- **Cubierto**: el dato queda **tapiado del todo** (lo importante: si queda un trozo visible, no sirve).
- **Toca**: al menos parte del dato queda tapada (margen de seguridad).
- **Precisión**: de todo lo que se tapa, qué parte es realmente un dato personal. Lo demás es texto inocente borrado.
- **Falsos positivos por documento**: cuántas cosas inocentes se tapan en cada página. Cada una obliga a la persona revisora a deshacerla.
- **Empresas tapadas**: si el documento tapa personas jurídicas, que no debería.
- **Velocidad y memoria**.

Para que las cifras sean honestas, la configuración «mejorada» se ajustó con un corpus y se **valida con otro distinto**: otra semilla y formatos que el ajuste no había visto (más direcciones abreviadas, teléfonos con paréntesis, nombres que no estaban en el ajuste). Si la diferencia entre ambos es grande, la configuración está sobreajustada.

## 6. Resultados

### 6.1 Cuánto mejora el ajuste (castellano, `es_core_news_md`, 150 documentos)

| | Datos cubiertos del todo | Al menos tocados | Precisión | Texto inocente tapado por página | Empresas tapadas |
|---|---|---|---|---|---|
| **base** (de serie) | 71,2 % | 80,2 % | 62,8 % | 6,3 | 100 % |
| **ajustada** | 89,2 % | 93,1 % | 78,1 % | 3,7 | 0 % |
| **mejorada** | **100 %** | **100 %** | **98,8 %** | **0,17** | 0 % |

De serie, solo 7 de cada 10 datos quedan tapados y se tapa texto inocente 6 veces por página. Con la configuración mejorada no se queda nada visible y apenas hay que deshacer nada.

### 6.2 Qué se acierta por tipo de dato

Datos cubiertos del todo, en castellano con `es_core_news_md`:

| Tipo | base | ajustada | mejorada |
|---|---|---|---|
| Nombres de personas | 97 % | 97 % | **100 %** |
| DNI | 77 % | 77 % | **100 %** |
| NIE | 100 % | 100 % | **100 %** |
| Direcciones | 3 % | 56 % | **100 %** |
| Teléfonos | 85 % | 94 % | **100 %** |
| Correos | 100 % | 100 % | **100 %** |
| IBAN | 100 % | 100 % | **100 %** |
| Matrículas | 1 % | 55 % | **100 %** |
| Referencias catastrales | 1 % | 100 % | **100 %** |

Los identificadores con dígito de control (NIE, IBAN, correo) funcionan de serie. Lo que había que construir era todo lo demás: direcciones, matrículas, catastral y los formatos con puntos, espacios o prefijo.

En catalán (`ca_core_news_md`) el patrón se repite: 59,3 % de serie y **96,7 %** con la configuración mejorada; la precisión pasa de 69,5 % a 93,3 %.

### 6.3 La prueba de fuego: corpus que el ajuste no había visto

| Idioma | Corpus de ajuste | Corpus de validación | Diferencia |
|---|---|---|---|
| Castellano | 100 % | **94,4 %** | −5,6 puntos |
| Catalán | 96,7 % | **88,9 %** | −7,8 puntos |

Con formatos nuevos (DNI con espacio, direcciones abreviadas «Av.», «Pl.», teléfonos con paréntesis) el acierto baja. **Hay algo de sobreajuste**, concentrado en tres cosas:

- **DNI con espacio** (`12345678 S`): cae al 69 %.
- **Direcciones con abreviaturas** (`Av.`, `Pl.`): 74 % en castellano y 59 % en catalán.
- Nombres y apellidos que no estaban en el ajuste: se mantienen bien (100 % y 87 %).

Nada queda roto, pero confirma lo esperado: **el ajuste hay que hacerlo con documentos reales del Colegio**, no con los ficticios.

### 6.4 Qué pasa cuando el OCR se equivoca

Errores de OCR simulados por sustitución de caracteres (S↔5, O↔0, l↔1…), castellano con la configuración mejorada:

| Errores de OCR | Datos cubiertos | Precisión | Texto inocente tapado por página |
|---|---|---|---|
| Ninguno | 100 % | 98,8 % | 0,17 |
| 1 % | 96,6 % | 92,1 % | 1,13 |
| 4 % | 89,1 % | 78,1 % | 3,43 |

**Con un 4 % de errores, uno de cada diez datos se queda sin tapar.** Es el dato más importante del informe: la anonimización no puede fiarse de un OCR malo. Refuerza la decisión de no transcribir las páginas por debajo del umbral de contraste y de marcar las lecturas dudosas antes de anonimizar.

### 6.5 Velocidad y memoria

`es_core_news_md`, configuración mejorada, sobre páginas de unas 1.700 letras:

| Medida | Valor |
|---|---|
| Tiempo por página | **65 ms** (mediana) |
| Páginas por hora | ~54.000 |
| Carga del modelo al arrancar | ~3 s |
| Memoria | 339 MB |

Comparado con el OCR (1,3 s por página con GPU), la anonimización supone **un 5 % del tiempo**: no es el cuello de botella.

### 6.6 Qué modelo elegir (castellano)

| Modelo | Datos cubiertos | Precisión | Memoria |
|---|---|---|---|
| `es_core_news_sm` | 90,3 % | 69,4 % | 163 MB |
| **`es_core_news_md`** | **100 %** | **98,8 %** | **339 MB** |
| `es_core_news_lg` | 100 % | 84,0 % | 889 MB |

El `lg` no mejora el acierto y confunde más (más texto inocente tapado, 2,7 por página frente a 0,17). **El `md` es el equilibrio**: el `sm` se queda corto y el `lg` ocupa 2,6 veces más memoria para nada.

## 7. Conclusiones

1. **Presidio sirve, y en local.** Detecta bien lo que tiene forma fija y se puede validar (DNI, NIE, IBAN, correo) y, con modelos de spaCy, los nombres y lugares. No necesita GPU ni salir del servidor.
2. **De serie no basta.** Tapa 7 de cada 10 datos y borra texto inocente 6 veces por página. Con la configuración mejorada: **9,4 de cada 10 datos tapados, con apenas 0,1 tapados de más por página** (sobre documentos que el ajuste no había visto).
3. **Lo que aporta el ajuste propio** no es «mejor modelo», sino formatos y reglas: dirección completa, matrícula, referencia catastral, DNI con puntos, teléfonos con prefijo, nombres en mayúsculas y catalanes con «i», y no tocar personas jurídicas.
4. **El punto débil es el OCR.** Con un 4 % de errores, uno de cada diez datos se escapa. La anonimización depende del semáforo de calidad y de la revisión humana.
5. **Cuesta poco.** 65 ms por página y 339 MB: un 5 % del tiempo del OCR.
6. **Recomendación**: `es_core_news_md` y `ca_core_news_md` con la configuración «mejorada», y antes de dar el POC por bueno, repetir la medición con 100-200 páginas reales anonimizadas del Colegio, que es justo la fase 0 de la propuesta.

## 8. Limitaciones

- Corpus **sintético**: reproduce los formatos habituales de una sentencia, pero no la variedad de un documento real (tablas, sellos, texto manuscrito, escaneos torcidos). La siguiente prueba debe hacerse con páginas reales anonimizadas del Colegio.
- Los errores de OCR se simulan por sustitución de caracteres. Un OCR real también se salta palabras y descoloca el texto.
- Medido en CPU, con un solo documento a la vez. No se ha probado el servidor definitivo ni en paralelo.
- El catalán solo se ha probado con el modelo `ca_core_news_md`; el castellano, con tres tamaños.
- No se ha probado el reconocimiento de **firmas y sellos en la imagen**, que la propuesta pide. Presidio tiene un módulo de imagen, pero necesita un OCR con coordenadas (Tesseract).
- La lista de municipios e instituciones que no se tapan es corta: en producción haría falta el nomenclátor completo.

## 9. Siguiente

- [ ] Repetir con páginas reales anonimizadas del Colegio (fase 0 de la propuesta).
- [ ] Probar el modelo catalán `ca_core_news_lg` y un modelo transformer.
- [ ] Decidir entre PDF nuevo (recomendado) o segundo OCR para tapar la imagen.
- [ ] Mover la configuración «mejorada» al código del backend, con su lista de excepciones versionada.
