# Estructura del backend (CSharp)

- **Para**: entrega del lunes 30/11/2026 (ver [[Equipo]])
- **Estado**: **alternativa documentada** · no seleccionada · 23/11/2026
- **Autor**: @ia-opencode-ruben
- **Qué es**: alternativa escrita en C#. Es ventajosa si Presidio sale del backend como servicio independiente; no sustituye a la estructura Python aceptada.
- **Dónde mirar**: el *por qué* del stack está en [[Enfoque tecnico]] y el contrato en [`docs/api/endpoints.md`](../../docs/api/endpoints.md).

## 1. Frontera

El backend **no implementa PaddleOCR-VL**: el OCR es responsabilidad de @Alex y se consume por HTTP. @Rubén implementa la anonimización con Presidio y la composición del PDF. @Yaser orquesta el recorrido del dato sin implementar motores. Como Presidio es Python, C# consume un servicio local de Presidio por HTTP o ejecuta el mismo contenedor compartido; no se integra mediante el runtime de .NET.

## 2. Stack

.NET 10 (LTS), ASP.NET Core **Minimal APIs**, `Npgsql` y `Dapper`. Sin ORM, sin AutoMapper, sin MediatR.

| Qué | Con qué | Por qué |
|---|---|---|
| HTTP y JSON | `Microsoft.AspNetCore` (framework) | Viene en el SDK: routing, *binding*, validación de tipos, OpenAPI |
| BD | `Npgsql` + `Dapper` | SQL explícito, mapeo a `record` sin inventarse un modelo paralelo |
| Config | `IConfiguration` + `IOptions<T>` | `.env` o variables de entorno; nada en el repo |
| Pruebas | `xUnit` + `WebApplicationFactory` + PostgreSQL real | Sin mocks de base de datos |
| Contenedor | `mcr.microsoft.com/dotnet/aspnet:10` *chiseled* | ~110 MB, sin shell, usuario no root |

## 3. Árbol

```
backend/
  Backend.sln
  Directory.Build.props          # Nullable=enable, TreatWarningsAsErrors
  Dockerfile
  src/
    Api/
      Api.csproj
      Program.cs                 # DI, pipeline, mapeo de endpoints
      Endpoints/
        AuthEndpoints.cs  UsersEndpoints.cs  DocumentsEndpoints.cs
        ReviewEndpoints.cs  AnonymizeEndpoints.cs  ExportEndpoints.cs
        RulesEndpoints.cs  AdminEndpoints.cs
      Middleware/
        RequestLogMiddleware.cs  # request_id + duración
        ErrorHandler.cs          # IExceptionHandler
      Security/
        TokenAuthenticationHandler.cs
      RateLimiting.cs            # configuración; el middleware lo pone el framework
    Application/
      Application.csproj
      Contracts/                 # records de entrada y salida
        AuthDtos.cs  UserDtos.cs  DocumentDtos.cs  ReviewDtos.cs  CommonDtos.cs
      Services/
        AuthService.cs  UserService.cs  DocumentService.cs
        ReviewService.cs  ExportService.cs  RuleService.cs
      Abstractions/              # lo que implementa Infrastructure
        IDocumentStore.cs  IEtlClient.cs  IFileStorage.cs
      Jobs/
        OcrJob.cs  PdfJob.cs
    Infrastructure/
      Infrastructure.csproj
      Data/
        Database.cs              # NpgsqlDataSource
        DocumentStore.cs         # Dapper
        Sql/  documents.sql  review.sql  reports.sql
      Etl/  EtlClient.cs       # OCR, Presidio y PDF como servicios HTTP
      Storage/  FileStorage.cs
  tests/
    Api.Tests/  Application.Tests/
```

La dirección de dependencias la impone el compilador: `Api` → `Application`, `Infrastructure` → `Application`, y `Application` no conoce ni ASP.NET ni Npgsql. Si algún día sobra una capa, se colapsa en una sola `Api.csproj` sin tocar la lógica; hoy no sobra.

## 4. Imports previstos

### `Program.cs`

```csharp
using Api.Endpoints;
using Api.Middleware;
using Api.Security;
using Application.Abstractions;
using Application.Services;
using Infrastructure.Data;
using Infrastructure.Etl;
using Infrastructure.Storage;
using Microsoft.AspNetCore.Authentication;
```

### `Api/Endpoints/DocumentsEndpoints.cs`

```csharp
using Application.Contracts;
using Application.Services;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.AspNetCore.Mvc;
```

### `Api/Middleware/ErrorHandler.cs`

```csharp
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using Npgsql;
```

### `Api/Middleware/RequestLogMiddleware.cs`

```csharp
using System.Diagnostics;
```

### `Api/Security/TokenAuthenticationHandler.cs`

```csharp
using System.Security.Claims;
using System.Text.Encodings.Web;
using Application.Abstractions;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;
```

### `Api/RateLimiting.cs`

```csharp
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;
```

### `Application/Services/DocumentService.cs`

```csharp
using Application.Abstractions;
using Application.Contracts;
```

### `Application/Abstractions/IDocumentStore.cs`

```csharp
using Application.Contracts;
```

### `Infrastructure/Data/Database.cs`

```csharp
using Npgsql;
using Microsoft.Extensions.Configuration;
```

### `Infrastructure/Data/DocumentStore.cs`

```csharp
using Application.Abstractions;
using Application.Contracts;
using Dapper;
using Npgsql;
```

### `Infrastructure/Etl/EtlClient.cs`

```csharp
using System.Net.Http.Json;
using Application.Abstractions;
```

### `Api/Api.csproj`

```xml
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Npgsql" Version="10.*" />
    <PackageReference Include="Dapper" Version="2.*" />
  </ItemGroup>
</Project>
```

## 5. Los cuatro middleware

| Tu fichero | Aquí | Nota |
|---|---|---|
| `audit` | `RequestLogMiddleware` | `request_id` y duración por petición. Las **filas** de auditoría las escribe el servicio dentro de su transacción, no el middleware |
| `limit_rate` | `RateLimiting.cs` | No hay middleware propio: `AddRateLimiter` + `UseRateLimiter`. Se limita OCR/PDF, no las IP |
| `handler_error` | `ErrorHandler : IExceptionHandler` | `AddProblemDetails()` + `UseExceptionHandler()`. Nunca devuelve el mensaje de Npgsql ni el *stack* |
| `auth` | `TokenAuthenticationHandler` | Autentica y deja el `ClaimsPrincipal`. Autorizar es `RequireAuthorization("Revisor")` en cada endpoint |

La autorización por rol en el endpoint es lo que permite devolver 403 en un sitio y 404 en otro, y evita la lista de rutas exentas que se pudre en un middleware.

## 6. Lo que no hay

| Pieza | Por qué no |
|---|---|
| `Controllers/` | Minimal APIs: un `MapGroup` por dominio y un fichero por dominio |
| `Repositories/` | `DocumentStore` es la implementación de `IDocumentStore`: el nombre no cambia el trabajo |
| EF Core | SQL explícito; Dapper mapea a `record` sin modelo paralelo |
| AutoMapper | Dos líneas por DTO; un `record` y un constructor no necesitan librería |
| MediatR / CQRS | 40 rutas y una persona: `DocumentService` con 5 métodos se lee de un vistazo |
| FluentValidation | `System.ComponentModel.DataAnnotations` + un *endpoint filter* de 10 líneas. Si las reglas crecen, se añade |
| `Properties/` | En C# existe y aquí no se usa: la configuración va por `IOptions` |

## 7. Pendiente

- **`Dapper` y ningún ORM** ([[0013-consultas-sql-o-sqlalchemy-core]], cerrada el 23/11): Dapper deja el SQL tal cual y no declara el esquema; EF Core arrastra migraciones que chocan con Flyway.
- **Una `Api.csproj` o tres proyectos**: hoy tres; el compilador ayuda a defenderlo, pero cuesta un `ProjectReference` por capa.
- `Jobs/` solo tiene sentido cuando el OCR sea por página ([[Tablero]]).
- La validación automática de `DataAnnotations` en Minimal APIs no viene de serie: o filter propio o `MinimalApis.Extensions`.
