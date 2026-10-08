$ErrorActionPreference = 'Stop'
$assistantPython = 'D:\Software\WeChatGroupLab\venv\Scripts\python.exe'
$assistantRoot = $PSScriptRoot
$assistantScript = Join-Path $assistantRoot 'assistant_supervisor.py'
if (!(Test-Path -LiteralPath $assistantPython -PathType Leaf) -or !(Test-Path -LiteralPath $assistantScript -PathType Leaf)) {
    throw '找不到 D 盘 Python 或群助手启动程序。'
}
# No console window is opened. A local lock prevents duplicate supervisors.
Start-Process -FilePath $assistantPython -ArgumentList @('-u', ('"' + $assistantScript + '"')) -WorkingDirectory $assistantRoot -WindowStyle Hidden
Write-Output 'Mydex 启动器已运行。保持电脑微信登录，状态面板：http://127.0.0.1:8769/?mode=protocol'
