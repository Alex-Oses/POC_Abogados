# 0014 · Stack del backend: Python aceptado, C# y Java como alternativas

- **Estado**: Aceptada (2026-11-23, @Rubén)
- **Fecha**: 2026-11-20
- **Autor**: @ia-opencode-ruben
- **Se decide con**: @Rubén (backend), @Marina (BD), @Kevin (despliegue), @Alex (frontend y OCR), @Yaser (ETL)
- **Votos**: @Rubén (backend), 2026-11-23: **Python 3.12 + FastAPI**. El motivo principal es mantener todo el backend técnico en un único stack: API, Presidio y generación del PDF. C# y Java siguen documentados como alternativas si el backend se separa del servicio de Presidio.

## Contexto

[[0008-stack-backend]] se cerró el 20/11 con **Python 3.12 + FastAPI** por un motivo que ya no se sostiene: las tres piezas caras (OCR, Presidio y composición del PDF) se suponía que compartían una única frontera técnica. Tras la aclaración del equipo, las responsabilidades quedan separadas: @Alex implementa PaddleOCR-VL, @Rubén Presidio y el PDF final, y @Yaser el recorrido y la orquestación del dato sin implementar los motores.

Ese motivo ha cambiado. La frontera del [[Enfoque tecnico]] §2 deja el OCR fuera del backend: PaddleOCR-VL lo implementa @Alex y se consume por HTTP. Presidio es responsabilidad técnica de @Rubén y también puede aislarse en un servicio Python. El backend queda como lo que el contrato pide: 40 rutas REST y JSON, permisos, transacciones y auditoría sobre PostgreSQL.

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
| La frontera con el OCR  | HTTP; PaddleOCR-VL lo implementa y mide @Alex                                      |
| La frontera con Presidio | HTTP a un servicio Python aislado si el API es C#, Java o .NET; PDF y reglas las implementa @Rubén |
| El frontend             | Sin decidir. Con C# abre Blazor; con Java, Angular; con Python, lo que sea         |

## Los contenedores

Arquitectura aceptada:

- El backend Python contiene API, Presidio y composición del PDF.
- PaddleOCR-VL sigue separado como servicio de @Alex, con GPU.
- PostgreSQL se despliega como servicio propio.
- @Yaser decide la orquestación entre el backend y el OCR; no implementa los motores.
- C# solo volvería a tener ventaja si Presidio se separa en un servicio independiente y se mantiene fuera del backend.

### Valoración C# como alternativa

C# sería ventajoso **si Presidio queda fuera del backend como un servicio independiente**. Conserva tipado fuerte, buen rendimiento de I/O, Npgsql/Dapper maduro y poco código ajeno al contrato. En ese escenario, C# gestiona la API y delega la detección de datos personales al servicio Python de Presidio.

Python sigue siendo la elección para el POC: con Presidio dentro del mismo stack, evita el salto C#↔Python, la serialización HTTP de las propuestas de anonimización y un contenedor adicional. Java no aporta una ventaja equivalente para Presidio y añade más complejidad operativa.

## Decisión

**Python 3.12 + FastAPI**, `psycopg` 3, Pydantic y SQL explícito. Motivo: la API, Presidio y el PDF comparten un único runtime y lenguaje. Se simplifica el desarrollo, el despliegue y el paso de datos entre OCR revisado, detección y sustitución.

C# queda como alternativa seria si Presidio se separa del backend y se mantiene como servicio independiente. Java queda como alternativa para entornos donde el ICAT ya exige Spring/JVM.

La decisión la acepta @Rubén el 23/11/2026. C# y Java no se eliminan de la documentación: sirven de referencia si cambia la frontera técnica.

## Consecuencias

- **Python**: implementación vigente basada en [[Estructura del backend (Python)]]. SQL directo con `psycopg` y `.sql`, sin ORM.
- **C# o Java**: solo se retomarán si cambia el entorno o si Presidio se separa del backend. Sus estructuras siguen disponibles en [[Estructura del backend (CSharp)]] y [[Estructura del backend (Java)]].
- C# tiene más ventaja que Java si Presidio pasa a ser un servicio independiente, porque Npgsql/Dapper son ligeros y Minimal APIs reduce la superficie del API.
