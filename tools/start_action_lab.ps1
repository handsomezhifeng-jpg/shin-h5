$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskPort=3689
$taskUrl="http://127.0.0.1:$taskPort/"
try {
 $taskResponse=Invoke-WebRequest -Uri $taskUrl -TimeoutSec 2
 if($taskResponse.Content -match '角色动作模拟器'){ Write-Output "动作模拟器已运行：$taskUrl"; exit 0 }
 throw '审核端口被其他页面占用。'
} catch {
 if(Get-NetTCPConnection -LocalPort $taskPort -State Listen -ErrorAction SilentlyContinue){ throw '审核端口被占用，未停止其他服务。' }
}
$taskLogs=Join-Path $taskRoot 'outputs/action-lab'
New-Item -ItemType Directory -Path $taskLogs -Force | Out-Null
$taskPython=(Get-Command python).Source
$taskProcess=Start-Process -FilePath $taskPython -ArgumentList @((Join-Path $taskRoot 'tools/serve_action_lab.py'),'--port',"$taskPort") -WorkingDirectory $taskRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskLogs 'server.stdout.log') -RedirectStandardError (Join-Path $taskLogs 'server.stderr.log') -PassThru
@{pid=$taskProcess.Id;url=$taskUrl;startedAt=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskLogs 'server-process.json') -Encoding utf8
Write-Output "动作模拟器已在后台启动：$taskUrl"
