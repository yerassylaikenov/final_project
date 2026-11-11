# Opens Kubernetes Dashboard (web UI of the kind cluster running in Docker Desktop).
#   powershell -ExecutionPolicy Bypass -File open_k8s_dashboard.ps1
# On the login page press "Skip".
$ns = kubectl get ns kubernetes-dashboard --no-headers 2>$null
if (-not $ns) {
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml
    kubectl -n kubernetes-dashboard patch deployment kubernetes-dashboard --type=json `
        -p '[{\"op\":\"add\",\"path\":\"/spec/template/spec/containers/0/args/-\",\"value\":\"--enable-skip-login\"}]'
    kubectl create clusterrolebinding dashboard-admin --clusterrole=cluster-admin `
        --serviceaccount=kubernetes-dashboard:kubernetes-dashboard
    kubectl -n kubernetes-dashboard rollout status deployment/kubernetes-dashboard --timeout=240s
}
$cmd = "Write-Host '>>> kubectl proxy - Kubernetes Dashboard at http://localhost:8001 (do not close)' -ForegroundColor Cyan; kubectl proxy --port=8001"
$enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cmd))
Start-Process wt.exe -ArgumentList @("-w", "new", "--title", "`"kubectl proxy (Dashboard)`"", "--suppressApplicationTitle",
    "powershell.exe", "-NoLogo", "-NoExit", "-EncodedCommand", $enc)
Start-Sleep 3
Start-Process "http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/#/workloads?namespace=default"
