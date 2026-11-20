# 0009 · Identidad: SSO del ICAT y admin local de emergencia

- **Estado**: Aceptada (2026-11-20, @Rubén)
- **Fecha**: 2026-11-17
- **Autor**: @ia-opencode-ruben (a petición de @Rubén)
- **Se decide con**: @Rubén (backend), @Kevin (despliegue), @Marina (BD), @Alex (frontend)
- **Votos**: @Rubén (backend), 2026-11-18: **opción 3**, entendida como SSO sin gestión de cuentas y admin local **solo para desarrollo y pruebas**, no desplegado (ver [[0012-identidad-y-roles]]). Faltan @Kevin, @Marina y @Alex.

## Contexto

El proyecto tiene hoy dos respuestas incompatibles y ninguna escrita como decisión:

- La [[Propuesta ICAT]] pide **SSO Office 365**: el abogado entra con la cuenta del Colegio.
- El contrato ([`docs/api/endpoints.md`](../../docs/api/endpoints.md) §1) implementa **contraseñas locales** con invitación por email, y no hay proveedor de correo elegido.

Es el bloqueante B2 de [[Coherencia]] y bloquea a B1: de la respuesta depende qué tablas existen (`sesiones_usuario` siempre; `tokens_usuario` solo si hay contraseña), cómo se da de alta a la gente y si hay que montar SMTP. La maqueta ya dibuja la pantalla de login, así que también condiciona el frontend.

## Opciones

1. **Solo SSO Office 365** (OIDC). Sin contraseñas, sin invitaciones, sin proveedor de correo. Depende de que el ICAT registre la aplicación y de que su tenant esté disponible: si el proveedor cae o el ICAT retira el permiso, **nadie puede entrar**, ni siquiera a consultar lo ya aprobado.
2. **Solo cuentas locales** (lo que hay hoy). Contraseña Argon2id, invitación y reset por email. No depende de nadie de fuera, pero hay que mantener contraseñas, política, bloqueos y un SMTP, y el usuario tiene una cuenta más que recordar.
3. **SSO + un admin local de desarrollo.** SSO como camino normal; una cuenta local —una, no una por usuario— fuera del tenant, con contraseña fuerte, **solo para desarrollo y pruebas** (arrancar sin el ICAT, probar permisos). **No se despliega en producción**: en producción la única entrada es el SSO. Todo uso queda en `auditoria`.

## Decisión

**Aceptada: opción 3**, con la opción 2 (cuentas locales) como alternativa si el ICAT no puede dar SSO en plazo. Es la que recomienda @Rubén.

## Consecuencias

- `sesiones_usuario` **hace falta**: la sesión es de la aplicación, con tope de 3 dispositivos y logout remoto ([[0012-identidad-y-roles]], opción B elegida por @Rubén el 18/11). Delegarla en el token del ICAT ahorraría la tabla pero perdería U-16 a U-20.
- `tokens_usuario` **no se usa en producción**: no hay invitación ni reset por correo. La contraseña del admin de desarrollo se siembra por variable de entorno, no por enlace.
- `usuarios.password_hash` pasa a ser opcional y solo lo tiene el admin de desarrollo.
- El SSO exige registro de aplicación en el ICAT (redirect URI, secreto, grupos) y mapear los roles desde el directorio o desde `usuarios_roles`.
- El login local de desarrollo se audita siempre y no se despliega en producción.
- Si el ICAT no puede dar SSO en plazo, la opción 2 sigue siendo válida para el piloto y no cierra la puerta al SSO después.
