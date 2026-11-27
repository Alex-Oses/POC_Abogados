#!/usr/bin/env bash
# Arranca la app entera (PostgreSQL + backend/frontend) en Docker. Sin sudo.
#
#   bash scripts/arrancar_docker.sh              # construye la imagen si hace falta
#   bash scripts/arrancar_docker.sh --sin-build  # arranca con la imagen que ya hay
#
# Solo necesita el motor de Docker en marcha y que tu usuario pueda usarlo.
# No instala nada en el sistema, no toca systemd y no pide contraseña.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Falta Docker: https://docs.docker.com/engine/install/ (o Docker Desktop)."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "El motor de Docker no responde. Arráncalo y vuelve a intentarlo:"
  echo "  - Docker Desktop: abre la aplicación y espera a que la ballena esté verde."
  echo "  - Docker rootless en Linux: systemctl --user start docker"
  exit 1
fi

# backend/.env con secretos nuevos si no existe (no se sube: está en .gitignore).
if [ ! -f backend/.env ]; then
  echo "Creando backend/.env con claves nuevas..."
  cp backend/.env.example backend/.env
  CLAVE="$(head -c 32 /dev/urandom | base64 | tr '+/' '-_' | tr -d '\n')"
  PASS="$(head -c 64 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-20)"
  sed -i.bak "s|^STORAGE_KEY=.*|STORAGE_KEY=${CLAVE}|; s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=${PASS}|" backend/.env
  rm -f backend/.env.bak
fi

if [ "${1:-}" = "--sin-build" ]; then
  docker compose --env-file backend/.env up -d
else
  docker compose --env-file backend/.env up -d --build
fi

PUERTO="${APP_PUERTO:-8000}"
echo "Esperando a que la app responda en http://127.0.0.1:${PUERTO}/ (la primera vez tarda: V1..V15 y semilla del admin)..."
listo=0
if command -v curl >/dev/null 2>&1; then
  for _ in $(seq 1 90); do
    if curl -fsS "http://127.0.0.1:${PUERTO}/health" >/dev/null 2>&1; then listo=1; break; fi
    sleep 2
  done
fi

echo
if [ "$listo" = 1 ]; then
  echo "App:   http://127.0.0.1:${PUERTO}/"
else
  echo "La app aún no responde; mira los logs con:  docker compose --env-file backend/.env logs -f app"
fi
grep -E '^(ADMIN_EMAIL|ADMIN_PASSWORD)=' backend/.env || true
echo
echo "Parar:  docker compose --env-file backend/.env down        (-v borra también la base de datos)"
