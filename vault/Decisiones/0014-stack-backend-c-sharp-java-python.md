# 0014 · Stack del backend (reabierto): C#, Java o Python

- **Estado**: Propuesta
- **Fecha**: 2026-11-20
- **Autor**: @ia-opencode-ruben
- **Se decide con**: @Rubén (backend), @Marina (BD), @Kevin (despliegue), @Alex (frontend y OCR), @Yaser (ETL)
- **Votos**: @Rubén (backend), 2026-11-23: **C#**. Python no le convence para un proyecto serio y lo ve mejor que Java para este proyecto. Faltan @Marina, @Kevin, @Alex y @Yaser para el visto bueno, que llega por Teams y no por la bóveda.

## Contexto

[[0008-stack-backend]] se cerró el 20/11 con **Python 3.12 + FastAPI** por un motivo que ya no se sostiene: las tres piezas caras (OCR, Presidio y composición del PDF) son Python, así que un solo lenguaje evitaba un segundo runtime y un contrato interno.

Ese motivo ha cambiado. La frontera del [[Enfoque tecnico]] §2 deja el **ETL fuera del backend**: PaddleOCR-VL y Presidio son de @Yaser y se consumen por HTTP. El backend queda como lo que el contrato pide: 40 rutas REST y JSON, permisos, transacciones y auditoría sobre PostgreSQL. No comparte una línea de código con el ETL, así que **no gana nada por estar en su mismo lenguaje**.

Condición que hace barato reabrir: no hay ni una línea de backend escrita. Cambiar hoy cuesta una decisión; cambiar en enero cuesta un backend.

Los criterios que pone @Rubén, por orden de peso:

1. **Librerías**: usarlas, pero pocas y con un dueño claro. Nada de un `node_modules` con 800 paquetes.
2. **Legibilidad y experiencia**: el equipo tiene backend con Java, C# y Python.
3. **Separar responsabilidades**: que la estructura se pueda enseñar y defender.
4. **Despliegue y compatibilidad**: todo en Docker, con PostgreSQL y con el frontend (sin decidir).
5. **Tipado y seguridad**: que el lenguaje evite errores o ayude documentandolos.
6. **Velocidad**: lo menos importante; el cuello es la GPU y el usuario es un Colegio.

## Comparativa

| Criterio                             | Python + FastAPI                                                  | C# + ASP.NET Core                                                                            | Java + Spring Boot                                                                                                     |
| ------------------------------------ | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Librerías directas**               | 4 (`fastapi`, `uvicorn`, `pydantic`, `psycopg`) + ~10 transitivas | **2** (`Npgsql`, `Dapper`): routing, JSON, validación, OpenAPI y auth vienen en el framework | 1 BOM + ~5 *starters* → **~40 jars** transitivos                                                                       |
| **Legibilidad**                      | Muy poca ceremonia; el tipado es opcional                         | Poca ceremonia con Minimal APIs; tipos explícitos en la firma                                | Correcta, pero el flujo vive en anotaciones y en el contenedor de Spring                                               |
| **Tu experiencia**                   | Media                                                             | Alta                                                                                         | Alta                                                                                                                   |
| **Separar responsabilidades**        | `api/services/db`; se sostiene si el equipo se disciplina         | Proyectos o carpetas; el compilador impide dependencias circulares mal hechas                | Capas canónicas (controller/service/repository), pero con más piezas                                                   |
| **Tipado**                           | `mypy` opcional; Pydantic valida en la frontera                   | **Nullable reference types** activadas, `record`, `required`, *pattern matching* exhaustivo  | `record`, `sealed`, pero la nulabilidad no la comprueba el compilador sin herramientas extra (`@NullMarked`, NullAway) |
| **Errores en producción**            | Un `None` donde tocaba un objeto                                  | El compilador no deja; el `null` es explícito                                                | Igual que C# si el proyecto se configura bien                                                                          |
| **Docker**                           | Imagen `python:3.12-slim` + venv, ~150 MB; trivial                | `aspnet:10` *chiseled*, ~110 MB; `dotnet publish` y listo                                    | `eclipse-temurin:25-jre`, ~180-250 MB; *layered jar*                                                                   |
| **Compatibilidad**                   | PostgreSQL por `psycopg`                                          | PostgreSQL por `Npgsql` (el mejor driver de los tres)                                        | PostgreSQL por el driver de JDBC, perfectamente maduro                                                                 |
| **Velocidad**                        | Suficiente: 5 usuarios y el trabajo pesado está fuera             | Alta                                                                                         | La más alta con hilos virtuales, irrelevante aquí                                                                      |
| **Madurez del ecosistema**           | Alta                                                              | Alta                                                                                         | La más alta para backends de empresa                                                                                   |
| **Si mañana el ETL comparte código** | Gratis                                                            | Contrato HTTP o cliente generado                                                             | Contrato HTTP o cliente generado                                                                                       |

### Python + FastAPI

- **A favor**: es lo que ya está escrito en [[Estructura del backend (Python)]] y lo que menos ceremonia tiene; 4 dependencias; arrancar es `uvicorn`. Si el ETL necesitara compartir modelos, es el único que lo hace gratis.
- **En contra**: el tipado es un extra que hay que mantener a mano (`mypy` + Pydantic), y un refactor de columna no rompe nada hasta que se ejecuta. @Rubén lo prefiere menos. Y el argumento de «un solo lenguaje» ya no existe.

### C# + .NET (LTS vigente)

- **A favor**: **es el que menos piezas necesita**. El framework compartido trae routing, JSON, validación, OpenAPI y autenticación; solo se añaden `Npgsql` y `Dapper`. Minimal APIs dan un fichero por dominio sin controladores ni contenedor de DI invisible. La nulabilidad la comprueba el compilador. La imagen *chiseled* es la más pequeña. `record` + `switch` exhaustivo sobre uniones cerradas evitan media clase de bugs. Y si algún día el frontend se decide por Blazor, el equipo no cambia de lenguaje.
- **En contra**: `dotnet` es otro runtime que @Kevin tiene que meter en la imagen; no hay «equivalente gratis» a `pytest` con PostgreSQL real (hay que montar `Testcontainers` o una BD de test). El ecosistema de terceros es menor que el de Java, aunque aquí no hace falta.

### Java + Spring Boot

- **A favor**: el estándar de facto en backend de empresa; **Flyway es una herramienta Java**, así que migraciones y aplicación comparten ecosistema; los **hilos virtuales** (Java 21+) hacen que el código bloqueante escale sin `async`; Spring Security y Validation son maduros y muy documentados; si el ICAT acaba imponiendo Java, no hay sorpresa.
- **En contra**: para 40 rutas y una persona es **peso**: un BOM, varios *starters*, ~40 jars, un `pom.xml` o `build.gradle`, un contenedor de DI y anotaciones que esconden el flujo. Arranque de 2-4 s y 300-500 MB de memoria frente a 100-150 MB. La mitad del tiempo de «defender el proyecto» se va en explicar Spring, no el producto.

## Lo que no cambia con ninguna opción

| Pieza                   | Por qué                                                                            |
| ----------------------- | ---------------------------------------------------------------------------------- |
| PostgreSQL 14+ y Flyway | Sigue siendo el dueño del esquema; el backend solo lee y escribe SQL parametrizado |
| El contrato de 40 rutas | Es HTTP y JSON; no depende del lenguaje                                            |
| Docker                  | Las tres tienen imagen oficial y multi-stage                                       |
| La frontera con el ETL  | HTTP; el backend no importa Presidio ni PaddleOCR                                  |
| El frontend             | Sin decidir. Con C# abre Blazor; con Java, Angular; con Python, lo que sea         |

## Los contenedores

Pregunta de @Rubén: ¿el ETL es un contenedor, o el OCR y Presidio van por su cuenta? Sin decidir, y no lo decide el backend. Lo que sí se puede afirmar:

- El backend **solo necesita una URL** del ETL. Da igual si detrás hay un contenedor o tres.
- Lo razonable, por recursos, son **cuatro o cinco**: `db`, `api`, `etl`, `ocr` (con GPU) y `anonymizer` (CPU). OCR y Presidio no comparten ni GPU ni ciclo de vida.
- Si @Yaser prefiere un solo contenedor `etl` con PaddleOCR y Presidio dentro, el backend no cambia. Ese detalle se cierra en la frontera del [[Enfoque tecnico]] §2, no aquí.

## Decisión

**Propuesta de @ia-opencode-ruben: C# con ASP.NET Core Minimal APIs**, `Npgsql` + `Dapper` y SQL explícito. Motivo en una frase: es el que cumple los seis criterios con menos piezas que mantener, y el que mejor encaja con «pocas librerías, código legible y el compilador ayudando».

Java es la alternativa seria si el criterio que manda es «lo que el ICAT ya conoce» o si @Kevin prefiere un despliegue JVM. Python solo se queda si se prefiere no rehacer [[Estructura del backend (Python)]] y aceptar el tipado opcional a cambio de cero trabajo.

**La decide @Rubén**; esta nota no la cierra sola.

## Consecuencias

- **Si C# o Java**: se usa tal cual [[Estructura del backend (CSharp)]] o [[Estructura del backend (Java)]], ya escritas. Se mantienen las carpetas y la frontera; cambian ficheros, extensiones y los dos o tres helpers. [[0013-consultas-sql-o-sqlalchemy-core]] cambia de nombre: en C# la elección es `Dapper` frente a EF Core, y en Java `JdbcClient` frente a JPA.
- La decisión no la cierra el documento: [[Estructura del backend (Python)]], [[Estructura del backend (CSharp)]] y [[Estructura del backend (Java)]] son la misma propuesta en tres lenguajes, para comparar el código que habría que escribir.
- **Si Python**: no se toca nada, y 0008 vuelve a estar vigente sin más.
- El coste de decidir mal se paga en enero, no hoy: no hay código.
