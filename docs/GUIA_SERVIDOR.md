# Guía para montar la app en el servidor

Esta guía deja la app funcionando en un servidor Linux y accesible desde cualquier ordenador, también desde fuera de la red del Col·legi. Está pensada para Azure, pero vale para cualquier máquina con Ubuntu 24.04.

Todo lo que hace la app con los documentos (OCR, detección de datos personales, PDF) se ejecuta en el propio servidor. No se llama a ninguna IA externa. Solo hace falta Internet durante la instalación, para bajar paquetes y el modelo de OCR.

Si algo falla en cualquier paso, ve directo al apartado [Si algo falla](#si-algo-falla).

## 1. Qué necesitas antes de empezar

- Una máquina virtual con **Ubuntu 24.04**. Para el OCR real recomendamos 4 vCPU, 16 GB de RAM y 64 GB de disco. En el PC de Alex, con gráfica, el OCR tarda unos 5 segundos por página. En un servidor sin gráfica irá más lento: mídelo con los documentos de prueba (paso 7) antes de cargar trabajo de verdad.
- Acceso por SSH a esa máquina con un usuario que pueda usar `sudo`.
- Los datos de conexión a la base de datos de Marina, si se va a usar la suya: servidor, puerto, base, usuario y contraseña. Si no, la instalación monta una base de datos propia con el mismo modelo (V1 a V15).
- Opcional pero recomendable: un nombre de dominio para el servidor (ver paso 2).

## 2. Preparar la máquina en Azure

1. En la IP pública de la máquina, abre **Configuración** y rellena **Etiqueta de nombre DNS** (por ejemplo `icat-poc`). Azure te da gratis un dominio como `icat-poc.westeurope.cloudapp.azure.com`. Con él la web tendrá un certificado HTTPS válido y el navegador no mostrará avisos.
2. En el **grupo de seguridad de red** (NSG) de la máquina, añade reglas de entrada para los puertos **80** y **443** (TCP, desde cualquier origen). El 22 (SSH) ya suele estar abierto; si puedes, limítalo a tu IP.
3. No abras el 5432 (base de datos), el 8000 (la app por dentro) ni el 11434 (OCR). Solo escuchan dentro del servidor y así debe seguir.

Si la base de datos de Marina está en otra máquina, esa máquina tiene que aceptar conexiones desde la IP de este servidor en su puerto de PostgreSQL. Eso lo configura quien la administre.

## 3. Instalar

Conéctate por SSH, crea una carpeta para la app y descarga el instalador:

```bash
mkdir -p ~/icat && cd ~/icat
curl -fsSLO https://raw.githubusercontent.com/Alex-Oses/POC_Abogados/feat/backend-documentos/scripts/instalar_servidor.sh
```

Cuando el PR #55 se fusione, cambia `feat/backend-documentos` por `main` en esa URL.

Lanza la instalación con las opciones que te tocan:

```bash
# Con dominio y con la base de datos de Marina
DOMINIO=icat-poc.westeurope.cloudapp.azure.com \
DATABASE_URL='postgresql://USUARIO:CLAVE@SERVIDOR:5432/icat' \
bash instalar_servidor.sh

# Con dominio y base de datos propia en el servidor
DOMINIO=icat-poc.westeurope.cloudapp.azure.com bash instalar_servidor.sh
```

Pon la `DATABASE_URL` entre comillas simples, sobre todo si la contraseña lleva símbolos. Si la contraseña tiene `@`, `:` o `/`, escríbelos como `%40`, `%3A` y `%2F`.

La primera vez tarda un rato: en una máquina limpia, sin el modelo de OCR, la instalación tardó unos 5 minutos, y el modelo se descarga aparte según la velocidad de la conexión. Por el camino verás bloques que empiezan por `==`. Los más importantes:

- `== Base de datos`: comprueba la base de datos antes de seguir. Tiene que acabar en `LISTA para el backend`. Si sale `NO LISTA`, se detiene y te dice qué falta (una tabla, una columna, un permiso). Con la base de Marina, pásale esa salida a ella.
- `Admin: admin@icat.local · contraseña en .../admin_password.txt`: la contraseña del administrador no se muestra por pantalla ni se guarda en los logs. Está en ese fichero.

Al final debe aparecer `App en https://...`. Esa es la dirección para entrar desde cualquier ordenador.

Sin `DOMINIO` también funciona, con la IP pública, pero el certificado es propio y el navegador avisará la primera vez. Se puede aceptar el aviso, aunque para que lo use más gente conviene el dominio.

## 3 bis. Alternativa: todo en Docker, sin sudo

Si prefieres no depender del Python del servidor, el backend también corre en Docker (API y frontend en el mismo contenedor):

```bash
cd ~/POC_Abogados
bash scripts/arrancar_docker.sh
```

Crea `backend/.env` si falta (con `STORAGE_KEY` y `ADMIN_PASSWORD` aleatorios), construye la imagen y levanta PostgreSQL y la app. No necesita sudo. Ojo: el servicio `icat-app` que deja `instalar_servidor.sh` usa el puerto 8000; para convivir con él, `APP_PUERTO=8001 bash scripts/arrancar_docker.sh`.

Sin scripts, las mismas dos órdenes:

```bash
cd ~/POC_Abogados
docker compose up -d --build      # levanta BD y app; lee backend/.env solo
docker compose down               # parar (-v borra también la base de datos)
```

Los puertos publicados se cambian en el `.env` de la raíz (está en `.gitignore`), para no repetir banderas:

```bash
echo 'DB_PUERTO=5433' >> .env     # si el 5432 está ocupado por otro PostgreSQL
echo 'APP_PUERTO=8001' >> .env    # si el servicio icat-app ocupa el 8000
```

Dentro de la red de Docker la app siempre habla con `db:5432`; esos dos solo cambian lo que se publica en la máquina.

Para parar y liberar los puertos, `docker compose down` (sin sudo): borra los contenedores y con ellos desaparecen las publicaciones de 5433 y 8001. Si un puerto sigue ocupado después, casi siempre es un contenedor suelto de un `docker run` —`docker ps -a` lo enseña y `docker rm -f NOMBRE` lo quita— o el gestor de puertos de Docker rootless, que se reinicia sin sudo con `systemctl --user restart docker`.

## 4. Primer acceso

1. Lee la contraseña del admin y borra el fichero cuando la tengas apuntada:

   ```bash
   cat ~/icat/admin_password.txt
   rm ~/icat/admin_password.txt
   ```

2. Entra en la dirección del paso anterior con `admin@icat.local` y esa contraseña.
3. Sube uno de los PDF de prueba (paso 7) y comprueba que se transcribe.

## 5. Dar de alta a más personas

La app todavía no tiene pantalla de alta de usuarios (está prevista con el inicio de sesión del ICAT). Mientras tanto, se crean desde el servidor:

```bash
cd ~/icat/POC_Abogados
backend/.venv/bin/python scripts/crear_usuario.py ana@icatarragona.cat "Ana" "García López" transcriptor revisor
```

Los roles posibles son `transcriptor`, `revisor` y `admin`, y se pueden combinar. El script enseña una contraseña inicial una sola vez: pásasela a la persona por un canal privado. Si el correo ya existe, actualiza el nombre y los roles, y genera otra contraseña. Así se resetea una contraseña olvidada.

El nombre que pongas es el que sale en «Subido por» y el que se usa para relacionar las carpetas de SharePoint con cada persona.

## 6. Uso del día a día

La instalación deja estos scripts en `~/icat`:

| Script | Para qué |
|---|---|
| `./arrancar.sh` | Arranca la app (normalmente no hace falta: arranca sola al encender el servidor) |
| `./parar.sh` | La para |
| `./actualizar.sh` | Baja la última versión de GitHub y reinicia |
| `./logs.sh` | Muestra lo que hace la app en directo (Ctrl+C para salir) |
| `./diagnostico.sh` | Junta todo lo necesario para arreglar un fallo (ver abajo) |

### Copias de seguridad

Haz una copia al menos cada noche. Programarla es una sola línea:

```bash
crontab -e
# y añade al final:
30 2 * * * bash ~/icat/POC_Abogados/scripts/copia_seguridad.sh ~/icat >> ~/icat/logs/copias.log 2>&1
```

Cada copia queda en `~/icat/copias/` y se guardan las 14 últimas. Incluye la base de datos (si es la de Docker o si tienes acceso a la de Marina), los originales cifrados y el `.env`.

Ojo con el `.env`: lleva la `STORAGE_KEY`, que es la clave con la que se cifran los originales. Sin ella no se pueden abrir, así que guarda una copia fuera del servidor, en un sitio seguro. Por la misma razón, la carpeta `copias/` no se debe compartir.

### SharePoint (opcional)

Para que los PDF dejados en SharePoint entren solos, rellena las variables `SHAREPOINT_*` de `~/icat/POC_Abogados/backend/.env` y ejecuta `./actualizar.sh`. Qué significa cada una y cómo se registra la aplicación en Microsoft Entra está en `vault/Decisiones/0019-entrada-por-sharepoint.md`.

## 7. Documentos de prueba

Para probar sin usar datos reales:

```bash
cd ~/icat/POC_Abogados
backend/.venv/bin/python scripts/generar_pruebas.py
```

Crea 17 documentos ficticios en `pruebas/`: un DNI, nóminas, padrón, IRPF, una notificación de juzgado, un contrato con datos personales, una solicitud en catalán, expedientes de justicia gratuita completos e incompletos, escaneos limpios y degradados, una foto JPG, un PNG y un fichero falso que la app debe rechazar. Para bajártelos a tu ordenador:

```bash
scp -r usuario@servidor:~/icat/POC_Abogados/pruebas .
```

## Si algo falla

**Durante la instalación.** El instalador se detiene y escribe algo como:

```
ERROR en la línea 123 (código 1): <el comando que falló>
Envía este fichero para arreglarlo: /home/usuario/icat/logs/instalacion-20261127-101500.log
```

Envía ese fichero. Si la instalación llegó a crear la app, manda también el diagnóstico (abajo). Puedes volver a lanzar `instalar_servidor.sh` cuando quieras: no borra la base de datos ni el `.env`.

**Con la app ya instalada.** Ejecuta:

```bash
cd ~/icat && ./diagnostico.sh
```

Crea `logs/diagnostico-FECHA.txt` con todo lo necesario: sistema, versión, servicios, estado de la app y de la base de datos, OCR, puertos y los últimos mensajes de la app y de Caddy. Las contraseñas y claves salen como `***`. Aun así, échale un vistazo antes de enviarlo.

Para sacarlo del servidor:

```bash
scp usuario@servidor:~/icat/logs/diagnostico-*.txt .
```

Problemas habituales:

- **La web no carga desde fuera pero sí desde el servidor.** Faltan los puertos 80/443 en el NSG de Azure (paso 2).
- **El certificado no se emite con `DOMINIO`.** El dominio tiene que apuntar a la IP pública y el puerto 80 debe estar abierto, porque Let's Encrypt lo usa para comprobarlo. Mira `./diagnostico.sh`, apartado Caddy.
- **`NO LISTA` en la base de datos.** Falta algo en la base de datos de Marina (tabla, columna o permiso). El mensaje dice qué.
- **Los documentos se quedan en «En cua».** El OCR no está listo. En el diagnóstico, el apartado «Ollama» debe listar el modelo `PaddleOCR-VL`. Si el servidor no pudo descargarlo, copia la carpeta de modelos desde un PC que lo tenga (en Windows, `%USERPROFILE%\.ollama\models`) a `/usr/share/ollama/.ollama/models` y reinicia con `sudo systemctl restart ollama`.

## Lista de comprobación para la prueba en el servidor

Con los documentos de `pruebas/` (ver `pruebas/README.md`). Si algo no va, apunta el número y ejecuta `./diagnostico.sh`.

1. La web abre desde un portátil fuera de la red, con candado (HTTPS) y sin avisos si se usó `DOMINIO`.
2. Login como admin y con un usuario creado con `crear_usuario.py`.
3. Subir `01_dni.pdf` con doble transcripción: pasa a «Transcrit» y en la bandeja sale «Pujat per» y «Doble transcripció».
4. Subir a la vez del 02 al 14: se ponen en cola, avanzan y acaban. Apunta cuánto tarda cada página con el OCR real.
5. `17_no_es_pdf.pdf` sale en el aviso rojo de rechazados y no frena a los demás.
6. Abrir `10_pagina_ilegible.pdf`: la página 2 sale como ilegible.
7. En Revisió, editar texto con negrita o color, recargar y comprobar que sigue; validar páginas.
8. Justícia gratuïta con `08` (completo) y `09` (le falta documentación): la vista previa y el aviso de lo que falta.
9. Anonimizar `06_contrato_datos_personales.pdf`, exportar y abrir el `_anon.pdf`: no debe verse ningún nombre, DNI, IBAN, teléfono ni correo.
10. «PDF transcrit» de cualquier documento: baja `<nombre>_trans.pdf`.
11. Filtros de la bandeja y ZIP de varios documentos.
12. Reiniciar el servidor (`sudo reboot`): la app vuelve sola y los documentos a medias siguen en la cola.
13. `copia_seguridad.sh` crea la copia en `copias/`.
