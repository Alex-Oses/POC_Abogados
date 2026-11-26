#!/usr/bin/env bash
# Instala la app en un servidor Ubuntu 24.04 / Debian 12 y deja arrancar.sh, parar.sh y actualizar.sh
# junto a la carpeta del repo. Se usa desde cualquier PC de la red en https://<IP-del-servidor>/
#
# Uso:  bash instalar_servidor.sh [rama]     (OCR_MOCK=1 bash ... para no instalar Ollama)
# Idempotente: si el repo ya existe hace pull y no toca el .env ni la base de datos.
#
# Base de datos: PostgreSQL 16 en Docker con el modelo de Marina (V1..V15 + views.sql), aplicado
# por backend/db/init.sh la primera vez que se crea el volumen. Solo escucha en 127.0.0.1.
# triggers.sql y partitioning.sql (PR #52) no se aplican: el backend ya hace su trabajo y
# pg_partman no viene en la imagen postgres:16.
set -euo pipefail

RAMA="${1:-feat/backend-documentos}"   # pasar a main cuando se fusione el PR
REPO="${REPO:-https://github.com/Alex-Oses/POC_Abogados.git}"
BASE="$(pwd)"
APP="$BASE/POC_Abogados"
OCR_MOCK="${OCR_MOCK:-0}"
MODELO="hf.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF:latest"
USUARIO="$(id -un)"
IP="$(hostname -I | awk '{print $1}')"

echo "== Paquetes del sistema"
sudo apt-get update -y
sudo apt-get install -y git curl python3 python3-venv python3-pip caddy
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sudo sh
sudo docker compose version >/dev/null 2>&1 || sudo apt-get install -y docker-compose-plugin
python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' || { echo "ERROR: hace falta Python 3.12+ (Ubuntu 24.04 lo trae)"; exit 1; }

echo "== Código ($RAMA)"
if [ -d "$APP/.git" ]; then
  git -C "$APP" fetch origin && git -C "$APP" checkout "$RAMA" && git -C "$APP" pull --ff-only
else
  git clone -b "$RAMA" "$REPO" "$APP"   # repo privado: gh auth login antes, o https://<token>@github.com/...
fi

echo "== Entorno Python"
cd "$APP/backend"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .
.venv/bin/python -m spacy download es_core_news_md

if [ ! -f .env ]; then
  KEY="$(.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
  PASS="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(12))')"
  sed -e "s|^STORAGE_KEY=.*|STORAGE_KEY=$KEY|" \
      -e "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$PASS|" \
      -e "s|^OCR_MOCK=.*|OCR_MOCK=$OCR_MOCK|" .env.example > .env
  chmod 600 .env
  echo "   Admin: admin@icat.local / $PASS   (guardado en $APP/backend/.env)"
fi

if [ "$OCR_MOCK" != "1" ]; then
  echo "== Ollama + modelo OCR"
  command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
  sudo systemctl enable --now ollama
  until curl -fs http://localhost:11434 >/dev/null; do sleep 1; done
  ollama pull "$MODELO"
fi

echo "== Base de datos (modelo de Marina)"
cd "$APP"
sudo docker compose up -d db   # restart: unless-stopped la levanta sola tras reiniciar
until sudo docker compose exec -T db pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done

echo "== Servicio de la app (arranca solo al encender el servidor)"
sudo tee /etc/systemd/system/icat-app.service >/dev/null <<EOF
[Unit]
Description=POC Abogados (ICAT)
After=network-online.target docker.service ollama.service
Wants=network-online.target

[Service]
User=$USUARIO
WorkingDirectory=$APP/backend
# Un solo proceso y solo en local: la cola OCR vive dentro de él (decisión 0017) y Caddy pone el HTTPS.
ExecStart=$APP/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "== HTTPS con Caddy (certificado propio para la IP $IP)"
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
https://$IP, https://localhost {
	tls internal
	reverse_proxy 127.0.0.1:8000
}
EOF
sudo systemctl daemon-reload
sudo systemctl enable icat-app caddy
sudo systemctl restart caddy

echo "== Scripts de manejo"
cat > "$BASE/arrancar.sh" <<EOF
#!/usr/bin/env bash
set -e
cd "$APP" && sudo docker compose up -d db
sudo systemctl start icat-app
echo "App en https://\$(hostname -I | awk '{print \$1}')/   (aviso de certificado la primera vez: aceptar)"
EOF
cat > "$BASE/parar.sh" <<EOF
#!/usr/bin/env bash
sudo systemctl stop icat-app
cd "$APP" && sudo docker compose stop db
echo "Parada."
EOF
cat > "$BASE/actualizar.sh" <<EOF
#!/usr/bin/env bash
set -e
git -C "$APP" pull --ff-only
"$APP/backend/.venv/bin/pip" install -q -e "$APP/backend"
sudo systemctl restart icat-app
echo "Actualizada. Ojo: migraciones nuevas V16+ no se aplican solas a una base ya creada."
EOF
cat > "$BASE/logs.sh" <<EOF
#!/usr/bin/env bash
sudo journalctl -u icat-app -f
EOF
chmod +x "$BASE"/{arrancar,parar,actualizar,logs}.sh

if command -v ufw >/dev/null && sudo ufw status | grep -q active; then
  sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
fi

"$BASE/arrancar.sh"
echo
echo "Listo. Manejo: $BASE/arrancar.sh · parar.sh · actualizar.sh · logs.sh"
echo "SharePoint (opcional): rellena SHAREPOINT_* en $APP/backend/.env y ejecuta $BASE/actualizar.sh (decisión 0019)."
