# Sube la app al servidor y la arranca con Docker, todo desde el portátil (Windows trae ssh y scp).
#   powershell -ExecutionPolicy Bypass -File scripts\subir_servidor.ps1 -Servidor usuario@IP -Puerto 8443
# -SshPuerto si el SSH no está en el 22. Pide la contraseña o usa tu clave SSH.
# Sube solo lo que está en git (sin .env, venv ni documentos). Repetirlo actualiza sin borrar datos.
param(
    [Parameter(Mandatory)] [string] $Servidor,
    [int] $Puerto = 443,
    [int] $SshPuerto = 22,
    [string] $Dominio = ""
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$zip = Join-Path $env:TEMP "icat_app.tar.gz"
git archive --format=tar.gz -o $zip HEAD
if ($LASTEXITCODE) { throw "git archive ha fallado" }

Write-Host "== Subiendo a $Servidor"
scp -P $SshPuerto $zip "${Servidor}:icat_app.tar.gz"
if ($LASTEXITCODE) { throw "scp ha fallado: revisa usuario, IP y puerto SSH" }

Write-Host "== Instalando y arrancando (la primera vez tarda: Docker y modelo de OCR)"
$remoto = "mkdir -p ~/icat && tar -xzf ~/icat_app.tar.gz -C ~/icat && cd ~/icat && PUERTO=$Puerto DOMINIO='$Dominio' bash scripts/servidor_docker.sh"
ssh -t -p $SshPuerto $Servidor $remoto
if ($LASTEXITCODE) { throw "el arranque en el servidor ha fallado: mira el mensaje de arriba" }
