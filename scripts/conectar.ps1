# Prepara este clon para trabajar: Obsidian con auto-pull sobre vault/. Idempotente.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$vault = Join-Path $root 'vault'
$plugin = Join-Path $vault '.obsidian\plugins\obsidian-git'
New-Item -ItemType Directory -Force $plugin | Out-Null

if (-not (Test-Path "$plugin\main.js")) {
    $rel = Invoke-RestMethod https://api.github.com/repos/Vinzent03/obsidian-git/releases/latest
    foreach ($a in $rel.assets | Where-Object name -in 'main.js', 'manifest.json', 'styles.css') {
        Invoke-WebRequest -UseBasicParsing $a.browser_download_url -OutFile (Join-Path $plugin $a.name)
    }
}
if (-not (Test-Path "$plugin\data.json")) {
    # Solo pull: los cambios suben por PR, nunca push directo a main.
    [IO.File]::WriteAllText("$plugin\data.json", '{"autoPullOnBoot":true,"autoPullInterval":10,"autoSaveInterval":0,"autoPushInterval":0,"disablePush":true}')
}

$obsidian = Test-Path "$env:LOCALAPPDATA\Programs\Obsidian\Obsidian.exe"
if (-not $obsidian -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    winget install --id Obsidian.Obsidian -e --silent --accept-package-agreements --accept-source-agreements | Out-Null
    $obsidian = Test-Path "$env:LOCALAPPDATA\Programs\Obsidian\Obsidian.exe"
}
if ($obsidian) {
    # Se pasa el URI al exe porque el protocolo obsidian:// no existe hasta el primer arranque.
    Start-Process "$env:LOCALAPPDATA\Programs\Obsidian\Obsidian.exe" -ArgumentList ("obsidian://open?path=" + [uri]::EscapeDataString($vault))
    Write-Output "OK: boveda abierta en Obsidian. Acepta 'Confiar en el autor y activar plugins' la primera vez."
} else {
    Write-Output "AVISO: instala Obsidian (https://obsidian.md) y abre la carpeta $vault como boveda."
}
Write-Output "OK: plugin Git listo (pull al abrir y cada 10 min, sin push)."
