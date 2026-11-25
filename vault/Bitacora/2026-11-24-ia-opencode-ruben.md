# 2026-11-24 · @ia-opencode-ruben

## Hecho

- Revisión de la crítica: lo estructural ya estaba en `main` por los commits del 23/11 (`d9f3240`, `a1bb010`, `8b3cac5`, #46): el PDF es del backend y de @Rubén, E-39 se cerró con `pypdf` (BSD), 0014 acepta Python y B8 ya está resuelto en `Enfoque tecnico` §6.1. No se rehace nada de eso.
- [[Coherencia]]: B1 pasa a **Resuelto (24/11)**. `V15`, la vista, el trigger y el diccionario ya están alineados; queda validar desde cero en desarrollo.
- [[0012-identidad-y-roles]]: queda **Aceptada (24/11)** por @Rubén. @Kevin y @Alex pueden dejar constancia de conformidad por Teams, pero no bloquean la implementación.
- [[0014-stack-backend-c-sharp-java-python]]: nota de que las versiones de framework están escritas de memoria y se fijan al implementar; la conformidad del resto llega por Teams.
- [[Tablero]]: el pendiente del ICAT queda concretado —`GET /auth/sso/login` y `GET /auth/sso/callback` ya están redactados como propuesta; solo falta el registro OIDC— y la línea de identidad de «Hecho» dice «decidida», no «resuelta».

## Siguiente

- Validar desde cero `V15` con `flyway clean` + `migrate` y comprobar vista, trigger y diccionario ([[0015-identidad-en-v15]]).
- Alineación con el modelo ER definitivo: `V15` añade nombres/apellidos, email case-insensitive, sesión deslizante, campos de versión, relaciones de reglas y fechas de categorías. E-51 queda bloqueado porque los `bbox_*` legacy de `anotaciones_entidad` requieren decidir si se conservan o se eliminan con plan de datos.
- Pedir al ICAT el registro OIDC: cliente, secreto, `redirect_uri` y scopes. Sin eso no hay callback real, aunque el contrato ya esté escrito.

## Bloqueos / preguntas

- El ICAT es dependencia externa: 1-2 semanas de terceros. Mientras tanto funciona el admin local de desarrollo.
