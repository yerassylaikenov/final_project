# Live proof on this laptop: Docker Desktop + one terminal window with 4 panes
#   top-left:     kubectl get pods --watch          (pods of the stand, loadgen job appears)
#   top-right:    kubectl logs -f core (3 replicas)  ("dep-a lost -> flying on plan from memory")
#   bottom-left:  experiment.sh on (live, ~2.5 min)  (fault at 30 s, repair at 60 s, metrics)
#   bottom-right: docker stats                        (the kind node container working)
#   powershell -ExecutionPolicy Bypass -File open_live.ps1
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Enc($s) { [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($s)) }
function Head($t) { "Write-Host '>>> $t' -ForegroundColor Cyan; " }

$pods = (Head "kubectl get pods -o wide --watch   (kind cluster in Docker, core R=3)") +
    "kubectl get pods -o wide --watch"
$logs = (Head "kubectl logs -f -l app=core --prefix   (3 core replicas)") +
    "kubectl logs -f -l app=core --prefix --tail=4 --max-log-requests=6"
$exp = (Head "bash experiment.sh on   (LIVE run in Kubernetes, ~2.5 min)") +
    "Set-Location '$root\stand'; Start-Sleep 4; `$env:NAME='k8s_on_live'; & 'C:\Program Files\Git\bin\bash.exe' -c './experiment.sh on'"
$stats = (Head "docker ps + docker stats   (Kubernetes node = Docker container)") +
    "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'; Write-Host ''; docker stats resilience-control-plane"

$a = @("-w", "new", "--maximized",
    "--title", "`"Pods`"", "--suppressApplicationTitle", "powershell.exe", "-NoLogo", "-NoExit", "-EncodedCommand", (Enc $pods),
    ";", "split-pane", "-V", "--title", "`"core logs`"", "--suppressApplicationTitle", "powershell.exe", "-NoLogo", "-NoExit", "-EncodedCommand", (Enc $logs),
    ";", "move-focus", "left",
    ";", "split-pane", "-H", "--title", "`"experiment`"", "--suppressApplicationTitle", "powershell.exe", "-NoLogo", "-NoExit", "-EncodedCommand", (Enc $exp),
    ";", "move-focus", "right",
    ";", "split-pane", "-H", "--title", "`"docker stats`"", "--suppressApplicationTitle", "powershell.exe", "-NoLogo", "-NoExit", "-EncodedCommand", (Enc $stats))

# Docker Desktop dashboard (Containers view shows the kind node)
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Start-Sleep 3
Start-Process wt.exe -ArgumentList $a
Start-Process explorer.exe (Join-Path $root "stand\results")
