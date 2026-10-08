param([switch]$Disable, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$assistantScript = Join-Path $PSScriptRoot 'start-assistant.ps1'
$assistantPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$assistantName = 'WeChatGroupLab'
$assistantRunKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$assistantCommand = '"' + $assistantPowerShell + '" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $assistantScript + '"'
if (!(Test-Path -LiteralPath $assistantScript -PathType Leaf)) { throw '找不到群助手启动脚本。' }
$assistantExisting = Get-ItemPropertyValue -LiteralPath $assistantRunKey -Name $assistantName -ErrorAction SilentlyContinue
if ($assistantExisting -and $assistantExisting -ne $assistantCommand) { throw '同名自启项属于其他配置，未覆盖。' }
if ($CheckOnly) {
    Write-Output ('脚本检查通过；登录自启状态：' + [bool]$assistantExisting)
    exit 0
}
if ($Disable) {
    if ($assistantExisting) { Remove-ItemProperty -LiteralPath $assistantRunKey -Name $assistantName }
    Write-Output '已关闭 Mydex 登录自启。当前正在运行的助手不受影响。'
} else {
    if (!(Test-Path -LiteralPath $assistantRunKey)) { New-Item -Path $assistantRunKey -Force | Out-Null }
    New-ItemProperty -LiteralPath $assistantRunKey -Name $assistantName -Value $assistantCommand -PropertyType String -Force | Out-Null
    Write-Output '已开启 Mydex 的 Windows 登录后自启。电脑微信需要正常登录；新的微信会话首次请在任一监听群发一句话。'
}
