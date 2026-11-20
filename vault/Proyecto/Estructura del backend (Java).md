# Estructura del backend (Java)

- **Para**: entrega del 27/11/2026 (ver [[Equipo]])
- **Estado**: **borrador** · 20/11/2026 · se edita en este mismo fichero
- **Autor**: @ia-opencode-ruben
- **Qué es**: la misma propuesta que [[Estructura del backend (Python)]], escrita en Java. No decide nada: sirve para comparar con [[Estructura del backend (CSharp)]] antes de cerrar [[0014-stack-backend-c-sharp-java-python]].
- **Dónde mirar**: el *por qué* del stack está en [[Enfoque tecnico]] y el contrato en [`docs/api/endpoints.md`](../../docs/api/endpoints.md).

## 1. Frontera

El backend **no hace OCR, ni anonimiza, ni compone el PDF** ([[Enfoque tecnico]] §2). No hay `modules/ocr`: hay un `RestClient` en `integration/`. Si el OCR entra en el backend, entra en `jobs/`.

## 2. Stack

Java 25 (LTS) y **Spring Boot 4** con `spring-boot-starter-jdbc` (`JdbcClient`). Sin JPA, sin Hibernate, sin Lombok.

| Qué | Con qué | Por qué |
|---|---|---|
| HTTP y JSON | `spring-boot-starter-web` | Jackson incluido; un controlador por dominio |
| BD | `spring-boot-starter-jdbc` + `org.postgresql:postgresql` | `JdbcClient`: SQL explícito con parámetros nombrados |
| Validación | `spring-boot-starter-validation` | `jakarta.validation` en los `record` de entrada |
| Seguridad | `spring-boot-starter-security` | Es el *starter* más pesado; se paga por roles y CSRF resuelto |
| Config | `application.yml` + `@ConfigurationProperties` | Entorno por variable; nada de secretos en el repo |
| Pruebas | `spring-boot-starter-test` + Testcontainers | PostgreSQL real |
| Contenedor | `eclipse-temurin:25-jre` + *layered jar* | `-XX:MaxRAMPercentage=75` para no pasarse del límite |
| Concurrencia | hilos virtuales (`spring.threads.virtual.enabled=true`) | Código bloqueante que escala sin `async` |

Flyway sigue siendo el CLI que migra, **no** `flyway-core` al arrancar: el esquema no lo toca la aplicación.

## 3. Árbol

```
backend/
  pom.xml
  Dockerfile
  src/main/java/icat/backend/
    BackendApplication.java
    config/
      AppProperties.java        # @ConfigurationProperties: BD, ETL, límites
      SecurityConfig.java       # authorizeHttpRequests + roles
      WebConfig.java            # CORS, tamaño de subida (20 MB)
    api/
      AuthController.java  UserController.java  DocumentController.java
      ReviewController.java  AnonymizeController.java  ExportController.java
      RuleController.java  AdminController.java
      dto/
        AuthDtos.java  UserDtos.java  DocumentDtos.java  ReviewDtos.java  CommonDtos.java
    service/
      AuthService.java  UserService.java  DocumentService.java
      ReviewService.java  ExportService.java  RuleService.java
    repository/
      DocumentRepository.java  UserRepository.java  ReviewRepository.java
    integration/
      EtlClient.java  FileStorage.java
    security/
      TokenAuthFilter.java  Roles.java
    error/
      ApiException.java  ApiExceptionHandler.java
    jobs/
      OcrJob.java  PdfJob.java
  src/main/resources/
    application.yml
    db/queries/  documents.sql  review.sql  reports.sql
  src/test/java/icat/backend/
    DocumentApiTest.java  ReviewApiTest.java
```

En Java el controlador **sí** es una clase: `@RestController` es la forma idiomática, no un residuo de MVC. Cada uno tiene 4-6 métodos y no contiene lógica: valida, delega en `service/` y devuelve el DTO.

## 4. Imports previstos

### `BackendApplication.java`

```java
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
```

### `config/SecurityConfig.java`

```java
import icat.backend.security.TokenAuthFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
```

### `api/DocumentController.java`

```java
import icat.backend.api.dto.DocumentDtos.DocumentOut;
import icat.backend.api.dto.DocumentDtos.DocumentList;
import icat.backend.service.DocumentService;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
```

### `service/DocumentService.java`

```java
import icat.backend.error.ApiException;
import icat.backend.repository.DocumentRepository;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
```

### `repository/DocumentRepository.java`

```java
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
```

### `security/TokenAuthFilter.java`

```java
import icat.backend.service.AuthService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.web.filter.OncePerRequestFilter;
```

### `error/ApiExceptionHandler.java`

```java
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
```

### `integration/EtlClient.java`

```java
import java.time.Duration;
import org.springframework.web.client.RestClient;
```

### `config/AppProperties.java`

```java
import org.springframework.boot.context.properties.ConfigurationProperties;
```

### `pom.xml`

```xml
<dependencies>
  <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
  <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-jdbc</artifactId></dependency>
  <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-validation</artifactId></dependency>
  <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-security</artifactId></dependency>
  <dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId><scope>runtime</scope></dependency>
  <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-test</artifactId><scope>test</scope></dependency>
</dependencies>
```

### `application.yml`

```yaml
spring:
  datasource:
    url: ${DB_URL}
    username: ${DB_USER}
    password: ${DB_PASSWORD}
  threads:
    virtual:
      enabled: true
app:
  etl-url: ${ETL_URL}
  max-upload-mb: 20
```

## 5. Los cuatro middleware

| Tu fichero | Aquí | Nota |
|---|---|---|
| `audit` | `RequestIdFilter` (o un `HandlerInterceptor`) | `request_id` y duración. Las **filas** de auditoría las escribe el servicio |
| `limit_rate` | `RateLimitFilter` | Spring no trae limitador. Un `Map` con ventana fija basta para 5 usuarios; si hace falta precisión, Bucket4j es una dependencia más |
| `handler_error` | `@RestControllerAdvice` | Devuelve `ProblemDetail` (RFC 9457). `DataAccessException` se traduce sin filtrar el SQLSTATE ni el mensaje de PostgreSQL |
| `auth` | `TokenAuthFilter` + `SecurityConfig` | El filtro autentica; las reglas por ruta y rol van en `authorizeHttpRequests` |

## 6. Lo que no hay

| Pieza | Por qué no |
|---|---|
| JPA / Hibernate | El esquema es de Flyway y el SQL es explícito: `JdbcClient` no inventa un modelo paralelo |
| Lombok | `record` ya da constructor, `equals`, `hashCode` y `toString` |
| MapStruct | Dos líneas por DTO; un `record` con un `static from(...)` se lee mejor |
| Módulos Maven | Un `pom.xml`; las capas son paquetes. Con 40 rutas no compensa un reactor multi-módulo |
| Librería de rate limit | Un filtro de 30 líneas antes que una dependencia |
| `data/` | Se llama `repository/` y es el nombre que todo el mundo espera en Java |

## 7. Pendiente

- **`JdbcClient` o JPA** (la pregunta de [[0013-consultas-sql-o-sqlalchemy-core]] en versión Java): `JdbcClient` mantiene el SQL de Flyway como única verdad; JPA ahorra mapeo pero duplica el esquema.
- **Spring Security o filtro propio**: el starter pesa y trae CSRF, CORS y sesiones que aquí no se usan. La alternativa es un `OncePerRequestFilter` y comprobar roles a mano; menos dependencias, más código propio que auditar.
- `@PreAuthorize` (necesita `@EnableMethodSecurity`) frente a reglas por ruta en `SecurityConfig`: las reglas por ruta se leen de un tirón.
- `jobs/` solo tiene sentido cuando el OCR sea por página ([[Tablero]]).
