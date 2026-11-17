# 0009 · Identidad: SSO del ICAT y admin local de emergencia

- **Estado**: Propuesta
- **Fecha**: 2026-11-17
- **Autor**: @ia-opencode-ruben (a petición de @Rubén)
- **Se decide con**: @Rubén (backend), @Kevin (despliegue), @Marina (BD), @Alex (frontend)
- **Votos**: @Rubén (backend), 2026-11-17: **opción 3**. Faltan @Kevin, @Marina y @Alex.

## Contexto

El proyecto tiene hoy dos respuestas incompatibles y ninguna escrita como decisión:

- La [[Propuesta ICAT]] pide **SSO Office 365**: el abogado entra con la cuenta del Colegio.
- El contrato ([`docs/api/endpoints.md`](../../docs/api/endpoints.md) §1) implementa **contraseñas locales** con invitación por email, y no hay proveedor de correo elegido.

Es el bloqueante B2 de [[Coherencia]] y bloquea a B1: de la respuesta depende qué tablas existen (`sesiones_usuario` siempre; `tokens_usuario` solo si hay contraseña), cómo se da de alta a la gente y si hay que montar SMTP. La maqueta ya dibuja la pantalla de login, así que también condiciona el frontend.

## Opciones

1. **Solo SSO Office 365** (OIDC). Sin contraseñas, sin invitaciones, sin proveedor de correo. Depende de que el ICAT registre la aplicación y de que su tenant esté disponible: si el proveedor cae o el ICAT retira el permiso, **nadie puede entrar**, ni siquiera a consultar lo ya aprobado.
2. **Solo cuentas locales** (lo que hay hoy). Contraseña Argon2id, invitación y reset por email. No depende de nadie de fuera, pero hay que mantener contraseñas, política, bloqueos y un SMTP, y el usuario tiene una cuenta más que recordar.
3. **SSO + un admin local de emergencia.** SSO como camino normal; una cuenta local —una, no una por usuario— fuera del tenant, con contraseña fuerte, usada solo para entrar si el SSO falla: dar de alta, desbloquear o revocar sesiones. Todo uso queda en `auditoria`.

## Decisión

**Propuesta: opción 3.** Es la que recomienda @Rubén y la que se somete al resto del equipo.

## Consecuencias

- `sesiones_usuario` sigue siendo necesaria en las tres opciones: la sesión es de la aplicación, no del proveedor.
- `tokens_usuario` solo hace falta para el reset de la cuenta de emergencia; la invitación por email deja de existir para el resto.
- `usuarios.password_hash` pasa a ser opcional y solo lo tiene el admin local.
- El SSO exige registro de aplicación en el ICAT (redirect URI, secreto, grupos) y mapear el rol desde el directorio o desde `usuarios.rol`.
- El login local de emergencia se audita siempre y conviene avisar al supervisor cuando se use.
- Si el ICAT no puede dar SSO en plazo, la opción 2 sigue siendo válida para el piloto y no cierra la puerta al SSO después.
