#!/usr/bin/env bash
# Copia de seguridad: base de datos + originales cifrados + .env (lleva STORAGE_KEY: sin ella los
# originales no se pueden descifrar). Uso:  bash copia_seguridad.sh [carpeta base]
# Deja copias/icat-FECHA.tar.gz y conserva las 14 últimas. Para hacerla cada noche (crontab -e):
#   30 2 * * * bash /ruta/POC_Abogados/scripts/copia_seguridad.sh /ruta >> /ruta/logs/copias.log 2>&1
set -euo pipefail
BASE="${1:-$(pwd)}"
APP="$BASE/POC_Abogados"
DESTINO="$BASE/copias"
FECHA="$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$DESTINO"
umask 077   # la copia contiene datos personales y la clave: solo la lee el usuario

URL="$(grep '^DATABASE_URL=' "$APP/backend/.env" | cut -d= -f2-)"
if sudo -n docker compose -f "$APP/docker-compose.yml" ps -q db >/dev/null 2>&1 && [[ "$URL" == *@127.0.0.1:* ]]; then
  sudo docker compose -f "$APP/docker-compose.yml" exec -T db pg_dump -U postgres -Fc icat > "$TMP/bd.dump"
else
  pg_dump -Fc "$URL" > "$TMP/bd.dump"   # BD externa: necesita postgresql-client
fi
STORAGE="$(grep '^STORAGE_DIR=' "$APP/backend/.env" | cut -d= -f2-)"
STORAGE="${STORAGE:-storage}"
[[ "$STORAGE" = /* ]] || STORAGE="$APP/backend/$STORAGE"
mkdir -p "$STORAGE"   # sin documentos subidos aún no existe
tar -C "$(dirname "$STORAGE")" -cf "$TMP/storage.tar" "$(basename "$STORAGE")"
cp "$APP/backend/.env" "$TMP/env"
tar -C "$TMP" -czf "$DESTINO/icat-$FECHA.tar.gz" bd.dump storage.tar env
ls -1t "$DESTINO"/icat-*.tar.gz | tail -n +15 | xargs -r rm --
echo "$(date -Is) copia OK: $DESTINO/icat-$FECHA.tar.gz ($(du -h "$DESTINO/icat-$FECHA.tar.gz" | cut -f1))"
echo "Guárdala también fuera del servidor: lleva la clave STORAGE_KEY."
