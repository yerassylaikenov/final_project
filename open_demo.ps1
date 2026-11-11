# Opens everything for the defense: one Windows Terminal window with a tab per result,
# the report PDF and the screenshots folder.
#   powershell -ExecutionPolicy Bypass -File open_demo.ps1
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Title($t) { "Write-Host ('=' * 90) -ForegroundColor DarkCyan; Write-Host '  $t' -ForegroundColor Cyan; Write-Host ('=' * 90) -ForegroundColor DarkCyan; " }
function Cmd($c) { "Write-Host 'PS> $($c.Replace("'", "''"))' -ForegroundColor Yellow; $c; " }

$tabs = [ordered]@{
    "1 Tests" = (Title "STEP 1. Unit tests: 8 pattern tests + 5 metrics tests") +
        "Set-Location '$root\stand'; " + (Cmd "python -m unittest -v")

    "2 Metrics example" = (Title "STEP 2. metrics.py on the 20-request example (expected 0.30 / 1 / 360 / 0.70 / 45-1003-1004)") +
        "Set-Location '$root\stand'; " + (Cmd "Get-Content results\example_20.csv") + (Cmd "python metrics.py results\example_20.csv")

    "3 Pattern code" = (Title "STEP 3. Pattern in stand/core.py: refresh_plan() + do_work()") +
        "Set-Location '$root'; `$i=0; Get-Content stand\core.py | ForEach-Object { `$i++; if ((`$i -ge 16 -and `$i -le 22) -or (`$i -ge 71 -and `$i -le 114)) { '{0,4}  {1}' -f `$i, `$_ } }; "

    "4 Calculations" = (Title "TASKS 3-6. Calculations (control values)") +
        "Set-Location '$root'; " + (Cmd "python analysis\calc.py")

    "5 Final results" = (Title "PRACTICE. Final table: given / PATTERN=off / PATTERN=on") +
        "Set-Location '$root'; " + (Cmd "python show_results.py")

    "6 Local runs log" = (Title "Local runs on this laptop (real logs): off, on, PLAN_MAX_AGE_S=10") +
        "Set-Location '$root\stand'; " +
        "foreach (`$n in 'off','on','on_maxage10') { Write-Host ''; Write-Host ('--- results\' + `$n + '.log') -ForegroundColor Yellow; Get-Content (Join-Path results (`$n + '.log')) | Where-Object { `$_ -notmatch '^\[loadgen\] t=' } }; "

    "7 Kubernetes" = (Title "Kubernetes: kind cluster inside Docker Desktop, core replicas R=3") +
        "Set-Location '$root'; " + (Cmd "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'") +
        (Cmd "kubectl get nodes") + (Cmd "kubectl get deploy,pods,svc") +
        (Cmd "kubectl apply --dry-run=server -f k8s-plan\flight-control.yaml")

    "8 K8s experiment log" = (Title "Kubernetes experiment.sh off / on (real console output)") +
        "Set-Location '$root\stand'; " + (Cmd "Get-Content results\k8s_off_console.txt") + "Write-Host ''; " +
        (Cmd "Get-Content results\k8s_on_console.txt") + "Write-Host ''; " +
        (Cmd "Get-Content results\k8s_on.log")

    "9 LIVE demo" = (Title "LIVE DEMO - type one of these commands:") +
        "Set-Location '$root\stand'; " +
        "Write-Host '  python run_local.py off --quick                                  # 30 s, fault 10-20 s' -ForegroundColor Green; " +
        "Write-Host '  python run_local.py on --quick' -ForegroundColor Green; " +
        "Write-Host '  python run_local.py on --quick --name q5 --env PLAN_MAX_AGE_S=5   # predict: POFOD ~ 0.17' -ForegroundColor Green; " +
        "Write-Host '  bash experiment.sh on                                            # Kubernetes, ~2.5 min' -ForegroundColor Green; " +
        "Write-Host ''; "
}

$args = @("-w", "new", "--maximized")
$first = $true
foreach ($name in $tabs.Keys) {
    $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($tabs[$name]))
    if (-not $first) { $args += ";"; $args += "new-tab" }
    $args += @("--title", "`"$name`"", "--suppressApplicationTitle", "powershell.exe", "-NoLogo", "-NoExit", "-EncodedCommand", $enc)
    $first = $false
}
$args += @(";", "focus-tab", "-t", "0")
Start-Process wt.exe -ArgumentList $args

Start-Process (Join-Path $root "report\report.pdf")
Start-Process explorer.exe (Join-Path $root "screenshots")
