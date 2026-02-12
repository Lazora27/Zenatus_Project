Param(
  [string]$Time = "00:00"
)
$taskName = "ZenatusTreeAgentEnhanced"
$base = "/opt/Zenatus_Backtester"
$py = "$base\Zenatus_Backtest_venv\Scripts\python.exe"
$script = "$base\02_Agents\tree_agent_enhanced.py"
$action = New-ScheduledTaskAction -Execute $py -Argument $script -WorkingDirectory $base
$triggerDaily = New-ScheduledTaskTrigger -Daily -At ([DateTime]::Parse($Time))
$triggerStartup = New-ScheduledTaskTrigger -AtStartup
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest -LogonType ServiceAccount
try {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
} catch {}
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($triggerDaily,$triggerStartup,$triggerLogon) -Settings $settings -Principal $principal -Description "Daily project tree and metrics snapshot (enhanced)"
Write-Output "Scheduled task '$taskName' registered. Outputs: 10_Tree\\Projectstructure\\Daily (md, html, json) + 10_Tree\\Projectstructure\\filemetrics_history.csv + 10_Tree\\Projectstructure\\project_metrics_timeline.html"
