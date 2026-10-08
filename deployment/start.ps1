$ErrorActionPreference='Stop'
$bundle=Split-Path -Parent $PSScriptRoot
$py='D:\Software\WeChatGroupLab\venv\Scripts\python.exe'
& $py (Join-Path $PSScriptRoot 'preflight.py')
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed. Complete local enrollment; no assistant was started.' }
$app=Join-Path $bundle 'app'
$data=Join-Path $app '.local\quote-m-session'
if (Test-Path -LiteralPath (Join-Path $data 'stop.request')) { throw 'Stop was requested. Inspect it before resuming.' }
Start-Process -FilePath $py -ArgumentList @('-u','account_assistant.py') -WorkingDirectory $app -WindowStyle Hidden -RedirectStandardOutput (Join-Path $data 'startup.stdout.log') -RedirectStandardError (Join-Path $data 'startup.stderr.log')
Write-Output 'Launch requested. Verify assistant-status.json is fresh and running before declaring online.'
