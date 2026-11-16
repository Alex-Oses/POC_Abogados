# POC Abogados · Transcripción y anonimización de documentos para el ICAT

> **🤖 ¿Eres una IA y te han pedido conectarte a este repo?** Sigue la sección «Primera conexión» de [AGENTS.md](AGENTS.md) sin esperar más instrucciones.
>
> **Persona:** pide a tu IA «conéctate a https://github.com/Alex-Oses/POC_Abogados» y lo hará sola.

Prueba de concepto para el **Il·lustre Col·legi de l'Advocacia de Tarragona (ICAT)**: una herramienta **100 % local**, en catalán y castellano, que lee documentos escaneados (empezando por los expedientes de **justicia gratuita**), deja revisar cada página junto a su imagen y anonimiza los datos personales antes de compartir o publicar.

> La herramienta ayuda a leer, no decide. Toda transcripción y toda anonimización la valida una persona antes de exportar.

## Estado

| Pieza | Estado | Dónde |
|---|---|---|
| Propuesta funcional y de diseño | Hecha (06/11/2026) | [vault/Proyecto/Propuesta ICAT](vault/Proyecto/Propuesta%20ICAT.md) |
| Pruebas de rendimiento del OCR (PaddleOCR-VL 1.6) | Hechas | [vault/Proyecto/Rendimiento OCR](vault/Proyecto/Rendimiento%20OCR.md) |
| Contrato de la API (v1) | Borrador | [vault/Proyecto/API](vault/Proyecto/API.md) |
| Modelo de datos (PostgreSQL) | Primer borrador | [docs/architecture](docs/architecture/README.md) |
| Código de la aplicación | Sin empezar | — |

## Qué hace

1. **Bandeja** (*Safata*): entran PDF e imágenes, a mano o desde la carpeta del escáner. Cada página lleva un semáforo de calidad.
2. **OCR local** con [PaddleOCR-VL 1.6](vault/Proyecto/Rendimiento%20OCR.md) sobre Ollama: ~1 % de errores de carácter y 100 % de DNI e importes exactos en escaneos normales; ~2.750 páginas/hora con una RTX 3050 de 4 GB. Ningún documento sale del servidor.
3. **Revisión**: imagen a la izquierda, texto editable a la derecha, con las dudas marcadas (dos lecturas distintas, DNI/NIE con letra incorrecta, IBAN inválido).
4. **Anonimización** según la práctica del CENDOJ y el RGPD: censurar, borrar, etiquetar, seudónimo o iniciales, por categoría de dato.
5. **Exportación** a PDF buscable o Word, eliminando de verdad el texto original (capa de texto, imagen y metadatos).

## Arquitectura prevista

```
Cliente web (CA/ES, identidad ICAT)
        │  HTTPS · Bearer token
        ▼
API REST  /api/v1   ──►  OCR: Ollama + PaddleOCR-VL 1.6 (GPU local)
        │                 Semáforo: contraste antes, texto después
        ▼
PostgreSQL 14+  (documentos, versiones, anotaciones, revisiones, auditoría con hash encadenado)
Almacenamiento cifrado en reposo para los originales
```

Endpoints v1 (borrador): `POST /transform/document`, `/transform/plain-text`, `/transform/build`, `/user/register`, `/user/login`. Detalle en [vault/Proyecto/API](vault/Proyecto/API.md).

## Estructura del repositorio

```
docs/architecture/   Modelo de datos: migraciones Flyway V1–V12, vistas, triggers, RGPD, diagrama
vault/               Bóveda de Obsidian: conocimiento, tablero, decisiones y bitácora del equipo (personas e IAs)
.github/             Plantilla de PR y comprobaciones automáticas
AGENTS.md            Instrucciones para agentes de IA (CLAUDE.md apunta aquí)
CONTRIBUTING.md      Cómo trabajar con ramas y PRs
```

## Puesta en marcha

### Base de datos

```bash
# PostgreSQL 14+ con uuid-ossp, pgcrypto (y pg_partman para partitioning.sql)
flyway -url=jdbc:postgresql://localhost:5432/icat_anon -locations=filesystem:docs/architecture/migrations migrate
psql -d icat_anon -f docs/architecture/views.sql
psql -d icat_anon -f docs/architecture/triggers.sql
```

### Motor de OCR

```bash
# Ollama con el GGUF oficial de PaddleOCR-VL 1.6 (0,9B, 1,8 GB)
OLLAMA_NUM_PARALLEL=4 ollama serve
# POST /api/generate · prompt "OCR:" · imagen en base64 · temperature 0
# num_ctx 4096 · repeat_penalty 1.05 · num_predict 1500 (si llega al tope, reintento con repeat_penalty 1.2)
```

Requisitos mínimos: GPU NVIDIA con 4 GB de VRAM y 16 GB de RAM (sin GPU funciona, ~6 veces más lento).

## Cómo trabajamos

- Nadie empuja directamente a `main`: todo entra por **Pull Request** con al menos una aprobación. Ver [CONTRIBUTING.md](CONTRIBUTING.md).
- La carpeta [`vault/`](vault/Inicio.md) es una **bóveda de Obsidian versionada en el propio repo**: cada `git pull` la actualiza para todo el equipo. Personas e IAs la usan para el tablero de tareas, las decisiones y la bitácora.
- Cada PR debe tocar algo en `vault/` (al menos una entrada de bitácora). Un PR sin cambios en la bóveda falla la comprobación salvo que su título lleve `[sin-vault]`.

## Privacidad

Nunca subas documentos reales del ICAT, datos personales ni credenciales a este repositorio. Para pruebas usa datos ficticios.
