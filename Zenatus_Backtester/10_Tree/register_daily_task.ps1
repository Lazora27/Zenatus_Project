Param(
  [string]$Time = "00:00"
)
$taskName = "ZenatusTreeAgent"
$py = "/opt/Zenatus_Backtester\Zenatus_Backtest_venv\Scripts\python.exe"
$script = "/opt/Zenatus_Backtester\10_Tree\tree_agent.py"
$action = New-ScheduledTaskAction -Execute $py -Argument $script -WorkingDirectory "/opt/Zenatus_Backtester"
$trigger = New-ScheduledTaskTrigger -Daily -At ([DateTime]::Parse($Time))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
try {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
} catch {}
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Description "Daily project tree and metrics snapshot"
Write-Output "Scheduled task '$taskName' registered. Outputs: Projectstructure\\Daily (md, html, json) + Projectstructure\\filemetrics_history.csv + project_metrics_timeline.html"
