$ErrorActionPreference = 'Stop'
$labPython = 'D:\Software\WeChatGroupLab\venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $labPython)) { $labPython = (Get-Command python).Source }
Set-Location -LiteralPath $PSScriptRoot
& $labPython server.py
