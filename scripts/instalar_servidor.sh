#!/usr/bin/env bash
# Instala la app en un servidor Ubuntu 24.04 / Debian 12. Deja arrancar.sh, parar.sh, actualizar.sh
# y logs.sh junto a la carpeta del repo. La web queda accesible desde fuera de la red por HTTPS.
#
# Uso (desde la carpeta donde quieras la app):
#   bash instalar_servidor.sh [rama]
# Variables opcionales:
#   DOMINIO=icat-poc.westeurope.cloudapp.azure.com   certificado real de Let's Encrypt (recomendado;
#                                                    en Azure: IP pública > Configuración > etiqueta DNS)
#   DATABASE_URL=postgresql://usuario:clave@host:5432/icat   usar la BD de Marina en vez de la de Docker
#   OCR_MOCK=1                                       sin modelo de OCR (pruebas)
#
# Sin IA externa: el OCR (PaddleOCR-VL en Ollama), Presidio/spaCy y el localizador (RapidOCR) corren
# en el propio servidor. Solo se descarga de Internet durante la instalación (paquetes y modelos).
# Idempotente: si el repo ya existe hace pull y no toca el .env ni la base de datos.
set -euo pipefail

RAMA="${1:-feat/backend-documentos}"   # pasar a main cuando se fusione el PR
REPO="${REPO:-https://github.com/Alex-Oses/POC_Abogados.git}"
BASE="$(pwd)"
APP="$BASE/POC_Abogados"
OCR_MOCK="${OCR_MOCK:-0}"
DOMINIO="${DOMINIO:-}"
BD_EXTERNA="${DATABASE_URL:-}"
MODELO="hf.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF:latest"
USUARIO="$(id -un)"
IP_LAN="$(hostname -I | awk '{print $1}')"

# --- Log: todo lo que sale por pantalla va también a logs/instalacion-FECHA.log --------------
mkdir -p "$BASE/logs"
LOG="$BASE/logs/instalacion-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
fallo() {
  echo
  echo "ERROR en la línea $1 (código $2): $3"
  echo "Envía este fichero para arreglarlo: $LOG"
  echo "Y si puedes, el diagnóstico completo:  bash $APP/scripts/diagnostico.sh $BASE"
}
trap 'fallo $LINENO $? "$BASH_COMMAND"' ERR
echo "== Instalación $(date -Is) · rama $RAMA"
echo "   Sistema: $(. /etc/os-release && echo "$PRETTY_NAME") · $(uname -r) · $(nproc) CPU · $(free -h | awk '/Mem:/{print $2}') RAM · disco libre $(df -h "$BASE" | awk 'NR==2{print $4}')"
echo "   Opciones: DOMINIO=${DOMINIO:-no} · BD externa=$([ -n "$BD_EXTERNA" ] && echo sí || echo no) · OCR_MOCK=$OCR_MOCK"

echo "== Paquetes del sistema"
sudo apt-get update -y
sudo apt-get install -y git curl python3 python3-venv python3-pip caddy postgresql-client
if [ -z "$BD_EXTERNA" ]; then
  command -v docker >/dev/null || curl -fsSL https://get.docker.com | sudo sh
  sudo docker compose version >/dev/null 2>&1 || sudo apt-get install -y docker-compose-plugin
fi
python3 -c 'import sys; sys.exit(sys.version_info < (3, 12))' || { echo "ERROR: hace falta Python 3.12+ (Ubuntu 24.04 lo trae)"; exit 1; }

echo "== Código ($RAMA)"
if [ -d "$APP/.git" ]; then
  git -C "$APP" fetch origin && git -C "$APP" checkout "$RAMA" && git -C "$APP" pull --ff-only
else
  git clone -b "$RAMA" "$REPO" "$APP"   # repo privado: gh auth login antes, o https://<token>@github.com/...
fi

echo "== Entorno Python (todo local: Presidio, spaCy, RapidOCR)"
cd "$APP/backend"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .
.venv/bin/python -m spacy download es_core_news_md

if [ ! -f .env ]; then
  KEY="$(.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
  PASS="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(16))')"
  # produccion: cookie Secure y sin /docs públicos (la web está en Internet).
  sed -e "s|^ENTORNO=.*|ENTORNO=produccion|" \
      -e "s|^STORAGE_KEY=.*|STORAGE_KEY=$KEY|" \
      -e "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$PASS|" \
      -e "s|^OCR_MOCK=.*|OCR_MOCK=$OCR_MOCK|" .env.example > .env
  chmod 600 .env
  # La contraseña no va al log: se guarda aparte, solo legible por el usuario.
  ( umask 077; echo "admin@icat.local  $PASS" > "$BASE/admin_password.txt" )
  echo "   Admin: admin@icat.local · contraseña en $BASE/admin_password.txt (bórralo tras apuntarla)"
fi
if [ -n "$BD_EXTERNA" ]; then
  sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$BD_EXTERNA|" .env
fi

if [ "$OCR_MOCK" != "1" ]; then
  echo "== Ollama + modelo OCR (local, solo escucha en 127.0.0.1)"
  command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
  sudo systemctl enable --now ollama
  until curl -fs http://127.0.0.1:11434 >/dev/null; do sleep 1; done
  if ! ollama pull "$MODELO"; then
    echo "AVISO: no se pudo descargar el modelo. Sin Internet: copia la carpeta de modelos de un PC"
    echo "       que lo tenga (Windows: %USERPROFILE%\\.ollama\\models) a /usr/share/ollama/.ollama/models"
    echo "       y reinicia Ollama (sudo systemctl restart ollama)."
  fi
fi

echo "== Base de datos"
cd "$APP"
if [ -n "$BD_EXTERNA" ]; then
  echo "   BD externa (Marina): no se usa Docker"
else
  echo "   PostgreSQL 16 en Docker con el modelo de Marina (V1..V15 + vistas), solo en 127.0.0.1"
  sudo docker compose up -d db   # restart: unless-stopped la levanta sola tras reiniciar
  until sudo docker compose exec -T db pg_isready -U postgres >/dev/null 2>&1; do sleep 1; done
  sleep 3   # init.sh aplica las migraciones la primera vez
fi
backend/.venv/bin/python scripts/comprobar_bd.py "$(grep '^DATABASE_URL=' backend/.env | cut -d= -f2-)" \
  || { echo "ERROR: la base de datos no está lista para el backend (ver arriba)"; exit 1; }

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
# --proxy-headers: la IP real del usuario (no la de Caddy) llega a la auditoría.
ExecStart=$APP/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

if [ -n "$DOMINIO" ]; then
  echo "== HTTPS con Caddy: certificado de Let's Encrypt para $DOMINIO"
  SITIO="$DOMINIO"
  TLS=""
else
  # Sin dominio: certificado propio para la IP. Funciona desde fuera, pero el navegador avisa.
  IP_PUB="$(curl -fs --max-time 5 https://api.ipify.org || true)"
  echo "== HTTPS con Caddy: certificado propio para ${IP_PUB:-sin IP pública} y $IP_LAN"
  SITIO="https://$IP_LAN${IP_PUB:+, https://$IP_PUB}"
  TLS="tls internal"
fi
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
$SITIO {
	$TLS
	encode gzip
	header {
		Strict-Transport-Security "max-age=31536000"
		X-Content-Type-Options nosniff
		X-Frame-Options DENY
		Referrer-Policy no-referrer
		-Server
	}
	request_body {
		max_size 25MB
	}
	reverse_proxy 127.0.0.1:8000
}
EOF
sudo systemctl daemon-reload
sudo systemctl enable icat-app caddy
sudo systemctl restart caddy

echo "== Scripts de manejo"
URL="${DOMINIO:+https://$DOMINIO/}"
URL="${URL:-https://${IP_PUB:-$IP_LAN}/}"
cat > "$BASE/arrancar.sh" <<EOF
#!/usr/bin/env bash
set -e
exec > >(tee -a "$BASE/logs/manejo.log") 2>&1
echo "== arrancar \$(date -Is)"
[ -z "$BD_EXTERNA" ] && (cd "$APP" && sudo docker compose up -d db)
sudo systemctl start ollama 2>/dev/null || true
sudo systemctl start icat-app caddy
echo "App en $URL"
EOF
cat > "$BASE/parar.sh" <<EOF
#!/usr/bin/env bash
exec > >(tee -a "$BASE/logs/manejo.log") 2>&1
echo "== parar \$(date -Is)"
sudo systemctl stop icat-app
[ -z "$BD_EXTERNA" ] && (cd "$APP" && sudo docker compose stop db)
echo "Parada."
EOF
cat > "$BASE/actualizar.sh" <<EOF
#!/usr/bin/env bash
set -e
exec > >(tee -a "$BASE/logs/manejo.log") 2>&1
echo "== actualizar \$(date -Is)"
trap 'echo "ERROR en actualizar.sh: \$BASH_COMMAND · envía $BASE/logs/manejo.log o ejecuta $BASE/diagnostico.sh"' ERR
git -C "$APP" pull --ff-only
git -C "$APP" log --oneline -1
"$APP/backend/.venv/bin/pip" install -q -e "$APP/backend"
sudo systemctl restart icat-app
echo "Actualizada. Ojo: migraciones nuevas V16+ no se aplican solas a una base ya creada."
EOF
cat > "$BASE/logs.sh" <<EOF
#!/usr/bin/env bash
sudo journalctl -u icat-app -f
EOF
cat > "$BASE/diagnostico.sh" <<EOF
#!/usr/bin/env bash
# Junta en un solo fichero lo necesario para arreglar un fallo. Sin contraseñas ni claves.
exec bash "$APP/scripts/diagnostico.sh" "$BASE"
EOF
chmod +x "$BASE"/{arrancar,parar,actualizar,logs,diagnostico}.sh

if command -v ufw >/dev/null && sudo ufw status | grep -q active; then
  sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
fi

"$BASE/arrancar.sh"
echo
echo "Listo. Manejo: $BASE/arrancar.sh · parar.sh · actualizar.sh · logs.sh · diagnostico.sh"
echo "Log de esta instalación: $LOG"
echo "Acceso desde fuera: abre los puertos 80 y 443 hacia este servidor (Azure: grupo de seguridad de red, NSG)."
echo "SharePoint (opcional): rellena SHAREPOINT_* en $APP/backend/.env y ejecuta $BASE/actualizar.sh (decisión 0019)."
