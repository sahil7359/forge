# Registers Forge agent jobs in Windows Task Scheduler on Rig 2. Run as admin, once.
# Set these two paths for the Rig 2 checkout before running.
$py   = "C:\forge\agent\.venv\Scripts\python.exe"
$repo = "C:\forge"

$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

function Register-Forge($name, $trigger, $module) {
  $action = New-ScheduledTaskAction -Execute $py -Argument "-m forge_agent.$module" -WorkingDirectory "$repo\agent"
  Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Force
}

# Hourly nudges: daily 07:00, repeat every hour for 15h -> last run 22:00 IST (TechSpec §4)
$hourly = New-ScheduledTaskTrigger -Once -At 07:00 -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Hours 15)
$hourly.StartBoundary = (Get-Date -Hour 7 -Minute 0 -Second 0).ToString("yyyy-MM-dd'T'HH:mm:ss")
Register-Forge "Forge Nudge" $hourly "nudge"

Register-Forge "Forge Report" (New-ScheduledTaskTrigger -Daily -At 00:05) "report"

# 07:00 retry — report.py exits quietly when yesterday's report already exists (AppFlow Flow 5)
Register-Forge "Forge Report Retry" (New-ScheduledTaskTrigger -Daily -At 07:00) "report"

# Monthly archive: 1st at 00:25 (schtasks handles calendar monthly cleanly)
schtasks /Create /TN "Forge Archive" /SC MONTHLY /D 1 /ST 00:25 /F `
  /TR "`"$py`" -m forge_agent.archive"

Write-Host "Registered: Forge Nudge (hourly 07-22), Forge Report (00:05), Forge Archive (1st 00:25)"
