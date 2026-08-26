$taskNameMorning = "QQQ-TQQQ-Autotrade-0940"
$taskNameClose = "QQQ-TQQQ-Autotrade-1545"
$workdir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bat = Join-Path $workdir "run_cycle_and_log.bat"

if (-not (Test-Path -LiteralPath $bat)) {
    throw "Missing script: $bat"
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`""
$triggerMorning = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 9:40AM
$triggerClose = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 3:45PM
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskNameMorning -Action $action -Trigger $triggerMorning -Settings $settings -Principal $principal -Force | Out-Null
Register-ScheduledTask -TaskName $taskNameClose -Action $action -Trigger $triggerClose -Settings $settings -Principal $principal -Force | Out-Null

Write-Output "Installed tasks:"
Write-Output "- $taskNameMorning"
Write-Output "- $taskNameClose"
