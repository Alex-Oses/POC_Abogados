# Arrancar los Docker del proyecto

Hay **dos** ficheros de Compose y no son intercambiables: uno es el de desarrollo (el mío) y otro el del servidor (el de Alex). Esta página dice cuál es cuál, cómo arrancar cada uno sin pisar al otro y qué mirar cuando algo no va.

## Cuál es cuál

| | **Desarrollo** · `docker-compose.yml` | **Servidor** · `docker-compose.servidor.yml` |
|---|---|---|
| Para qué | programar y probar en tu equipo o en la VM | la máquina que se enseña desde fuera |
| Proyecto Compose | `poc_abogados` (sale del nombre de la carpeta) | `icat` (lo fija el fichero con `name:`) |
| Contenedores | `poc_abogados-db-1`, `poc_abogados-app-1` | `icat-secretos-1`, `icat-db-1`, `icat-app-1`, `icat-caddy-1`, `icat-aviso-1` |
| Qué levanta | PostgreSQL 16 y la app (API + frontend en un proceso) | secretos, PostgreSQL 16, la app, **Caddy con HTTPS** y un aviso con la URL |
| Qué publica | `127.0.0.1:5433` y `127.0.0.1:8010` (solo desde la propia máquina) | `0.0.0.0:${PUERTO:-8443}`, lo único accesible desde fuera |
| Datos | volúmenes `poc_abogados_icat_pg` y `poc_abogados_icat_storage` | `icat_pg`, `icat_storage`, `icat_secretos`, `icat_caddy` |
| Configuración | `.env` de la raíz (puertos) y `backend/.env` (opcional) | variables de entorno y el volumen `icat_secretos` |
| Admin | `ADMIN_EMAIL` / `ADMIN_PASSWORD` de `backend/.env` | se genera solo; lo imprime el servicio `aviso` |

Los dos se llaman distinto **a propósito**: `docker compose down` solo apaga contenedores del proyecto de la carpeta donde estás. Por eso un `down` en `~/POC_Abogados` deja vivos los `icat-*` del servidor.

## El de desarrollo

```bash
cd ~/POC_Abogados
printf 'DB_PUERTO=5433\nAPP_PUERTO=8010\n' > .env     # en la VM compartida, ver más abajo
bash scripts/arrancar_docker.sh                       # crea backend/.env si falta y espera a /health
curl -s http://127.0.0.1:8010/health                  # {"estado":"ok",...}
```

- El script construye la imagen, arranca BD y app, y al final imprime la URL y el `ADMIN_EMAIL`/`ADMIN_PASSWORD`. La siguiente vez, `bash scripts/arrancar_docker.sh --sin-build`.
- A mano es lo mismo: `docker compose up -d --build`.
- **Sin `--build` no se reconstruye la imagen.** Después de un `git pull`, `docker compose up -d` reutiliza la imagen vieja y el navegador sigue sirviendo el código anterior: hay que pasar `--build --force-recreate`.
- Logs: `docker compose logs -f app`. Parar: `docker compose down` (los datos se quedan en los volúmenes). `down -v` borra también la base de datos y los originales.
- Abrir la web desde la propia máquina: `http://127.0.0.1:8010`. Desde un portátil, túnel SSH (más abajo).

### Que el OCR llegue a Ollama

El compose **pisa** el `OLLAMA_URL` de `backend/.env`: dentro del contenedor vale lo que diga `OLLAMA_URL_DOCKER` en el `.env` de la raíz y, si no hay nada, `http://host.docker.internal:11434`. Con Docker rootless ese nombre no resuelve, así que lo más simple es dejar la IP privada de la máquina:

```bash
echo 'OLLAMA_URL_DOCKER=http://10.0.0.4:11434' >> .env    # la IP que da hostname -I
docker compose up -d --force-recreate app
```

Desde el PR #68 la app, si no hay red con la base configurada, prueba sola `host.docker.internal`, `10.0.2.2`, `172.17.0.1` y `127.0.0.1`, se queda con la que responde (deja `ocr_ollama_conectado` en el log) y guarda el motivo del fallo en la auditoría `OCR_FALLIDO`. Eso cubre el arranque limpio, pero si Ollama escucha en una IP concreta de la máquina, `OLLAMA_URL_DOCKER` es lo que lo resuelve.

## El del servidor

```bash
cd ~/POC_Abogados
docker compose -f docker-compose.servidor.yml up -d --build
docker compose -f docker-compose.servidor.yml logs aviso   # imprime la URL y la contraseña del admin
```

- Publica **un solo puerto**, `${PUERTO:-8443}`. Para usar otro, un `.env` junto al compose con `PUERTO=9443` (el 8443 tiene que estar abierto en el NSG de Azure o en el firewall de la red).
- La primera vez, el servicio `secretos` genera las contraseñas, la `storage_key` y un certificado propio. Después ese volumen manda: cambiar el `.env` no rota nada.
- Certificado propio → el navegador avisa la primera vez: *Avanzado → Continuar*.
- Actualizar: `git pull` y el mismo `up -d --build`. Los datos viven en los volúmenes.
- Parar: `... down`. Borrar **todo, datos incluidos**: `... down -v`.
- Si el recuadro `LISTO` ya pasó, la contraseña se lee del volumen:
  `docker run --rm -v icat_icat_secretos:/s:ro alpine:3.20 cat /s/admin_password`
- Logs de un servicio concreto: `docker compose -f docker-compose.servidor.yml logs -f app` (`db`, `caddy`…).

## Los dos a la vez en la misma VM

Son proyectos distintos, así que conviven sin problema: cada uno tiene su red, sus volúmenes y sus contenedores. Tres reglas:

1. Desde la carpeta de un compose, **solo** se para ese proyecto: `down` sin `-f` apaga el de desarrollo; `docker compose -f docker-compose.servidor.yml down` apaga el del servidor. Nunca el `down` del otro.
2. Nada de `docker system prune`, `docker rm -f` ni `docker kill` sobre contenedores que no sean tuyos: la VM es compartida y Alex puede estar transcribiendo.
3. Antes de levantar algo, mira quién ocupa el puerto:

```bash
ss -ltnp | grep -E ':(5432|5433|8000|8010|8443|9443|11434)\b'
docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

### La trampa: los dos se llaman `icat`

`docker-compose.servidor.yml` declara `name: icat`. Si lo lanzas tal cual en tu usuario, Compose cree que los `icat-app-1` / `icat-db-1` que ya están corriendo son **suyos** y los recrea, con lo que tumbas la app de Alex. Para probarlo sin tocar nada, dale otro nombre de proyecto y otro puerto:

```bash
PUERTO=9443 docker compose -f docker-compose.servidor.yml -p icat-ruben up -d --build
docker compose -f docker-compose.servidor.yml -p icat-ruben logs aviso
```

Eso crea `icat-ruben-*` con volúmenes propios (`icat-ruben_icat_pg`, `icat-ruben_icat_secretos`…), es decir, **base de datos y contraseña nuevas**, separadas de las de Alex. Para pararlo: el mismo comando con `-p icat-ruben down`.

### ¿De quién es un contenedor?

```bash
docker inspect -f '{{.Name}} · {{index .Config.Labels "com.docker.compose.project"}} · {{index .Config.Labels "com.docker.compose.project.working_dir"}}' $(docker ps -q)
```

`working_dir` dice la carpeta desde la que se lanzó: si es la tuya, es tuyo; si es la de Alex, no se toca.

## Puertos de la VM compartida `genai-openllm-vm`

| Puerto | Quién lo tiene | Qué hacer |
|---|---|---|
| 5432 | otro PostgreSQL de la máquina | la BD de desarrollo se publica en **5433** (`DB_PUERTO=5433`) |
| 5433 | nuestro PostgreSQL en Docker | — |
| 8000 | servicio `icat-app` de systemd (instalación antigua) | la app de desarrollo se publica en **8010** (`APP_PUERTO=8010`) |
| 8001 | otro servicio de la VM | no se usa |
| 8010 | nuestra app de desarrollo | — |
| 8443 | Caddy del compose del servidor (Alex) | para probarlo uno mismo, **9443** |
| 11434 | Ollama de la máquina | no se publica nunca; se llega a él por la IP privada |

Dentro de la red de Docker esos números no cambian: la app siempre habla con `db:5432` y escucha en su `8000`.

## Entrar desde otro ordenador

- **Desarrollo** (escucha solo en `127.0.0.1`, así que no acepta conexiones de fuera): túnel SSH desde tu portátil.

  ```bash
  ssh -L 8010:127.0.0.1:8010 b_ruben_munoz_blanco@IP_DE_LA_VM
  # y en el navegador: http://127.0.0.1:8010
  ```

- **Servidor**: `https://IP_DE_LA_VM:8443`. Si desde dentro de la VM funciona y desde fuera se queda cargando, el que corta es el firewall/NSG, no Docker.
- Nunca se abren el 5432, el 8000 ni el 11434: son internos.

## Cuando algo no va

| Síntoma | Qué es | Qué hacer |
|---|---|---|
| Un documento queda en «✕ Error d’OCR» | la app no llega a Ollama | `ss -ltnp \| grep 11434`, `curl http://IP:11434/api/tags` y `OLLAMA_URL_DOCKER` en el `.env` de la raíz |
| En el log, `404` del modelo | falta el modelo o no se llama igual | `ollama list` y `OCR_MODEL` con el nombre exacto |
| `Connection refused` en todas las bases | Ollama escucha solo en `127.0.0.1` | `OLLAMA_HOST=0.0.0.0:11434` en el servicio (reiniciarlo corta lo que se esté transcribiendo: avisa antes) |
| La web sigue con textos viejos | imagen sin reconstruir o caché | `up -d --build --force-recreate` y `Ctrl+Shift+R` en el navegador |
| `address already in use` | otro servicio tiene el puerto | cambiar `DB_PUERTO` / `APP_PUERTO` en el `.env` de la raíz |
| `dependency failed to start: container … is unhealthy` | un servicio no arrancó | el error real está justo encima en la salida |
| Un documento en «error» con ↻ Reintentar | quedó a medias | el botón lo devuelve a la cola sin perder las páginas ya leídas |

## Parar y limpiar

```bash
docker compose ps                     # qué está arriba en este proyecto
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker compose down --remove-orphans  # este proyecto; los datos se quedan
systemctl --user restart docker       # rootless: suelta puertos huérfanos, sin sudo
```

`down -v` borra los volúmenes: la base de datos, los originales cifrados y —en el servidor— las contraseñas y el certificado. Ahí empieza todo de cero, con admin y `storage_key` nuevos (los PDF antiguos dejan de poder abrirse). En la VM compartida, **nunca** `docker system prune`.
