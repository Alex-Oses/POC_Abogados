#!/usr/bin/env bash
# Monta toda la app con Docker en un Ubuntu (pensado para la VM de Azure) con un solo comando:
#   DOMINIO=icat-poc.westeurope.cloudapp.azure.com bash scripts/servidor_docker.sh
# Sin DOMINIO usa la IP pública con certificado propio (funciona, pero el navegador avisa).
# Volver a ejecutarlo actualiza: no toca .env ni los datos (volúmenes).
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "== Instalando Docker"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
fi
DOCKER="docker"; docker info >/dev/null 2>&1 || DOCKER="sudo docker"

if [ ! -f .env ]; then
  echo "== Creando .env con claves nuevas"
  # 32 bytes en base64 urlsafe = clave Fernet válida.
  KEY="$(head -c32 /dev/urandom | base64 | tr '+/' '-_')"
  if [ -n "${DOMINIO:-}" ]; then
    SITIO="$DOMINIO"; TLS=""
  else
    IP="$(curl -fs --max-time 5 https://api.ipify.org || hostname -I | awk '{print $1}')"
    SITIO="https://$IP"; TLS="tls internal"
  fi
  umask 077
  cat > .env <<EOF
COMPOSE_PROFILES=servidor
SITIO=$SITIO
TLS=$TLS
POSTGRES_PASSWORD=$(head -c24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9')
STORAGE_KEY=$KEY
ADMIN_EMAIL=admin@icat.local
ADMIN_PASSWORD=$(head -c18 /dev/urandom | base64 | tr -dc 'A-Za-z0-9')
EOF
fi

echo "== Arrancando (la primera vez baja imágenes y el modelo de OCR: puede tardar)"
git pull --ff-only 2>/dev/null || true
$DOCKER compose up -d --build

echo "== Esperando al modelo de OCR"
$DOCKER compose logs -f ollama-modelo 2>/dev/null | tail -n 3 || true

echo
echo "LISTO: $(grep '^SITIO=' .env | cut -d= -f2-)  (si es https://IP, acepta el aviso del certificado)"
echo "Usuario: admin@icat.local · contraseña: grep ADMIN_PASSWORD .env"
echo "Estado: docker compose ps · Logs: docker compose logs -f app"
