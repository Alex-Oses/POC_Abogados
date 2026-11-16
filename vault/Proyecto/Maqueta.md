# Maqueta navegable

`maqueta/index.html`: un único fichero sin dependencias. Ábrelo en el navegador. Datos ficticios, diseño de la [[Propuesta ICAT]] (granate `#B2051B`, Roboto, Georgia para el documento, semáforo con icono y texto) y CA/ES.

## Recorrido (la guía de abajo a la derecha lo sigue)

| # | Pantalla (`#ruta`) | Qué se ve |
|---|---|---|
| 1 | `#login` | Acceso con la cuenta del Colegio (Office 365), aviso de procesamiento local |
| 2 | `#safata` | KPI, zona para arrastrar, buscador, documentos con estado y semáforo. «Nou document» sube el expediente |
| 3 | `#processant` | 23 páginas, 4 en paralelo: contraste → lectura → semáforo. Pág. 22 ilegible (contraste 46 < 80) |
| 4 | `#revisio` | Imagen/texto lado a lado. Dos lecturas distintas (ámbar), DNI e IBAN con control incorrecto (granate). «Validar» bloqueado hasta resolver |
| 5 | `#jg` | Checklist del expediente, datos extraídos, aviso «orientativo, no vinculante», requerimiento y envío a tramitación |
| 6 | `#anonimitzar` | 6 formas, categorías con recuento, clic / Mayús+clic, ficha al pasar el ratón, vista original, lista de lo anonimizado |
| 7 | `#exportat` | Confirmación obligatoria, garantías y registro de auditoría |
| 8 | `#arxiu`, `#informes` | Búsqueda y panel (fase 2) |

## Pasarla a Figma

1. En Figma: plugin **html.to.design** → *Import from URL* (o su extensión de Chrome con la página abierta).
2. Importa cada `#ruta`; queda una pantalla por estado. Cierra la guía (✕) antes de importar.
3. Enlaza las pantallas con *Prototype* siguiendo la tabla.

## Comprobación

`maqueta/recorrido.py` recorre el flujo completo con Playwright sobre Edge, guarda 17 capturas, comprueba los bloqueos (validar y exportar) y falla si hay errores de JS:

```
pip install playwright
python maqueta/recorrido.py maqueta/index.html capturas
```
