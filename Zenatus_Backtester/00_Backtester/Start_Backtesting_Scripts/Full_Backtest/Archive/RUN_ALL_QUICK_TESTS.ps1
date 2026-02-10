# RUN ALL QUICK TESTS - PowerShell Batch Script
# ==============================================

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("="*79) -ForegroundColor Cyan
Write-Host "QUICK TEST LAUNCHER - ALL 4 TIMEFRAMES" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("="*79) -ForegroundColor Cyan
Write-Host ""

$scripts = @(
    @{TF="1H";  Script="QUICK_TEST_1H_PRODUCTION.py";  Est="5-8 min"},
    @{TF="30M"; Script="QUICK_TEST_30M_PRODUCTION.py"; Est="6-10 min"},
    @{TF="15M"; Script="QUICK_TEST_15M_PRODUCTION.py"; Est="8-12 min"},
    @{TF="5M";  Script="QUICK_TEST_5M_PRODUCTION.py";  Est="10-15 min"}
)

$scriptPath = "01_Backtest_System\Scripts"
$results = @()

for ($i = 0; $i -lt $scripts.Count; $i++) {
    $test = $scripts[$i]
    $num = $i + 1
    
    Write-Host ""
    Write-Host "=" -NoNewline -ForegroundColor Cyan
    Write-Host ("="*79) -ForegroundColor Cyan
    Write-Host "[$num/4] STARTING: $($test.TF) Quick Test (est. $($test.Est))" -ForegroundColor Green
    Write-Host "=" -NoNewline -ForegroundColor Cyan
    Write-Host ("="*79) -ForegroundColor Cyan
    Write-Host ""
    
    $fullPath = Join-Path $scriptPath $test.Script
    
    if (-not (Test-Path $fullPath)) {
        Write-Host "[ERROR] Script not found: $fullPath" -ForegroundColor Red
        $results += @{TF=$test.TF; Status="FAILED"; Detail="Not found"}
        continue
    }
    
    $startTime = Get-Date
    
    try {
        python $fullPath
        $elapsed = ((Get-Date) - $startTime).TotalMinutes
        
        if ($LASTEXITCODE -eq 0) {
            $results += @{TF=$test.TF; Status="SUCCESS"; Detail="{0:N1}min" -f $elapsed}
            Write-Host ""
            Write-Host "[$num/4] $($test.TF) COMPLETE! ({0:N1}min)" -f $elapsed -ForegroundColor Green
        } else {
            $results += @{TF=$test.TF; Status="FAILED"; Detail="Exit code $LASTEXITCODE"}
            Write-Host ""
            Write-Host "[$num/4] $($test.TF) FAILED!" -ForegroundColor Red
        }
    }
    catch {
        $results += @{TF=$test.TF; Status="ERROR"; Detail=$_.Exception.Message.Substring(0, [Math]::Min(50, $_.Exception.Message.Length))}
        Write-Host ""
        Write-Host "[$num/4] $($test.TF) ERROR: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("="*79) -ForegroundColor Cyan
Write-Host "ALL TESTS COMPLETE!" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("="*79) -ForegroundColor Cyan
Write-Host ""

Write-Host "SUMMARY:" -ForegroundColor Yellow
foreach ($result in $results) {
    $symbol = if ($result.Status -eq "SUCCESS") { "✓" } else { "✗" }
    $color = if ($result.Status -eq "SUCCESS") { "Green" } else { "Red" }
    Write-Host "  $symbol $($result.TF): " -NoNewline
    Write-Host "$($result.Status) ($($result.Detail))" -ForegroundColor $color
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("="*79) -ForegroundColor Cyan
Write-Host "Results saved in:" -ForegroundColor Yellow
Write-Host "  01_Backtest_System/Documentation/Quick_Test/[1h|30m|15m|5m]/" -ForegroundColor Cyan
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("="*79) -ForegroundColor Cyan
