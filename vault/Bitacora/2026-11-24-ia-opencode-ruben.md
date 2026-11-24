# 2026-11-24 · @ia-opencode-ruben

## Hecho

- Revisión de la crítica: lo estructural ya estaba en `main` por los commits del 23/11 (`d9f3240`, `a1bb010`, `8b3cac5`, #46): el PDF es del backend y de @Rubén, E-39 se cerró con `pypdf` (BSD), 0014 acepta Python y B8 ya está resuelto en `Enfoque tecnico` §6.1. No se rehace nada de eso.
- [[Coherencia]]: B1 pasa de «Resuelto» a **«Decidido, pendiente de implementar»**. `V15` sigue sin editar; el veredicto ya no dice que no quede nada abierto, sino que no quedan bloqueantes de diseño.
- [[0012-identidad-y-roles]]: retirada la línea que aún pedía a @Rubén confirmar `usuarios_roles`; esa confirmación está en `Votos` desde el 20/11. Sigue en **Propuesta** por @Kevin y @Alex.
- [[0014-stack-backend-c-sharp-java-python]]: nota de que las versiones de framework están escritas de memoria y se fijan al implementar; la conformidad del resto llega por Teams.
- [[Tablero]]: el pendiente del ICAT queda concretado —`GET /auth/sso/login` y `GET /auth/sso/callback` ya están redactados como propuesta; solo falta el registro OIDC— y la línea de identidad de «Hecho» dice «decidida», no «resuelta».

## Siguiente

- Editar `V15` con el SQL de 0012, recrear la base de desarrollo y actualizar `views.sql`, `triggers.sql` y `data-dictionary.md` ([[0015-identidad-en-v15]]).
- Pedir al ICAT el registro OIDC: cliente, secreto, `redirect_uri` y scopes. Sin eso no hay callback real, aunque el contrato ya esté escrito.

## Bloqueos / preguntas

- El ICAT es dependencia externa: 1-2 semanas de terceros. Mientras tanto funciona el admin local de desarrollo.
