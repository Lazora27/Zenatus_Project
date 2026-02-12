Param(
  [string]$Host = $env:REMOTE_HOST,
  [string]$User = $env:REMOTE_USER,
  [string]$KeyPath = $env:REMOTE_KEY,
  [string]$RemoteWorkDir = "/srv/zenatus/backtests",
  # 1:1 Dokumentationspfade wie lokal spiegeln
  [string]$RemoteOutDir = "/srv/zenatus/Zenatus_Dokumentation/Dokumentation/Fixed_Exit/1h",
  [string]$LocalOutDir = "/opt/Zenatus_Dokumentation\Dokumentation\Fixed_Exit\1h",
  [string]$LocalScript = "/opt/Zenatus_Backtester\00_Backtester\Start_Backtesting_Scripts\Full_Backtest\Archive\PRODUCTION_1H_FINAL.py"
)

if (-not $Host -or -not $User -or -not $KeyPath) {
  Write-Error "Bitte REMOTE_HOST, REMOTE_USER, REMOTE_KEY setzen oder als Parameter übergeben."
  exit 1
}

$ErrorActionPreference = "Stop"
function Invoke-SSH($cmd) {
  & ssh -i $KeyPath "$User@$Host" $cmd
}
function Invoke-SCPUpload($src, $dst) {
  & scp -i $KeyPath $src "$User@$Host:$dst"
}
function Invoke-SCPDownload($src, $dst) {
  & scp -i $KeyPath -r "$User@$Host:$src" $dst
}

Write-Output "== Remote Vorbereitung =="
# Erzeuge vollständige 1:1 Dokumentationsstruktur auf Server
Invoke-SSH "mkdir -p $RemoteWorkDir /srv/zenatus/Zenatus_Dokumentation/Dokumentation/Fixed_Exit/1h"
Write-Output "Upload Script: $LocalScript -> $RemoteWorkDir"
Invoke-SCPUpload $LocalScript "$RemoteWorkDir/"

Write-Output "== Starte Remote Backtest =="
# Python3 vorausgesetzt auf Server; Logs im RemoteOutDir
$remoteCmd = "cd $RemoteWorkDir && python3 $(Split-Path -Leaf $LocalScript) --out $RemoteOutDir"
Invoke-SSH $remoteCmd

Write-Output "== Synchronisiere Ergebnisse =="
New-Item -ItemType Directory -Force -Path $LocalOutDir | Out-Null
Invoke-SCPDownload "$RemoteOutDir/*" $LocalOutDir

Write-Output "Fertig. Ergebnisse unter: $LocalOutDir"
