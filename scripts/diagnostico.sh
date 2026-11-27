#!/usr/bin/env bash
# Junta en UN fichero todo lo que hace falta para arreglar un fallo del servidor.
# Uso:  bash diagnostico.sh [carpeta base]     (la carpeta que contiene POC_Abogados/ y logs/)
# Las claves, contraseñas y tokens se tapan antes de escribir nada.
BASE="${1:-$(pwd)}"
APP="$BASE/POC_Abogados"
mkdir -p "$BASE/logs"
SALIDA="$BASE/logs/diagnostico-$(date +%Y%m%d-%H%M%S).txt"

# Tapa valores sensibles: variables *KEY/*PASSWORD/*SECRET/*TOKEN, contraseñas en URLs y Bearer.
tapar() {
  sed -E -e 's/((KEY|PASSWORD|SECRET|TOKEN)[A-Z_]*=).*/\1***/I' \
         -e 's#(://[^:/@]+:)[^@]+@#\1***@#g' \
         -e 's/(Bearer )[A-Za-z0-9._~+-]+/\1***/g'
}
seccion() { echo; echo "===== $1 ====="; }

{
  echo "Diagnóstico $(date -Is) · $(hostname)"
  seccion "Sistema"
  (. /etc/os-release && echo "$PRETTY_NAME"); uname -r
  echo "CPU: $(nproc) · RAM: $(free -h | awk '/Mem:/{print $3" usada de "$2}')"
  df -h "$BASE" | tail -1
  seccion "Versión de la app"
  git -C "$APP" log --oneline -3 2>&1; git -C "$APP" status --short 2>&1 | head -20
  seccion "Configuración (.env sin secretos)"
  grep -v '^\s*#' "$APP/backend/.env" 2>&1 | grep . | tapar
  seccion "Servicios"
  for s in icat-app caddy ollama docker; do
    printf '%-9s %s\n' "$s" "$(systemctl is-active "$s" 2>/dev/null || echo '?')"
  done
  seccion "Salud de la app"
  curl -s -m 5 http://127.0.0.1:8000/health || echo "no responde en 127.0.0.1:8000"
  echo; curl -s -m 5 -o /dev/null -w "Caddy https local: %{http_code}\n" -k https://127.0.0.1/ || true
  seccion "Base de datos"
  if [ -x "$APP/backend/.venv/bin/python" ]; then
    "$APP/backend/.venv/bin/python" "$APP/scripts/comprobar_bd.py" 2>&1 | tapar
  fi
  (cd "$APP" && sudo -n docker compose ps 2>&1 | tail -3) || true
  seccion "Ollama / modelo OCR"
  curl -s -m 5 http://127.0.0.1:11434/api/tags | head -c 600 || echo "Ollama no responde"
  echo
  seccion "Puertos escuchando"
  (ss -ltnp 2>/dev/null || netstat -ltn 2>/dev/null) | grep -E ':(80|443|8000|5432|11434)\b'
  seccion "App: últimas 300 líneas (journalctl -u icat-app)"
  sudo -n journalctl -u icat-app -n 300 --no-pager 2>&1 | tapar
  seccion "Caddy: últimas 80 líneas"
  sudo -n journalctl -u caddy -n 80 --no-pager 2>&1 | tapar
  seccion "Caddyfile"
  tapar < /etc/caddy/Caddyfile 2>&1
  seccion "Último log de instalación (final)"
  ultimo="$(ls -t "$BASE"/logs/instalacion-*.log 2>/dev/null | head -1)"
  [ -n "$ultimo" ] && { echo "$ultimo"; tail -120 "$ultimo" | tapar; }
  seccion "Log de arrancar/parar/actualizar (final)"
  tail -60 "$BASE/logs/manejo.log" 2>/dev/null | tapar
} > "$SALIDA" 2>&1

echo "Diagnóstico guardado en: $SALIDA"
echo "Envía ese fichero. Ya va sin contraseñas ni claves, pero échale un vistazo antes."
