# Прогон в Killercoda (Kubernetes Playground)

Открыть https://killercoda.com/playgrounds/scenario/kubernetes и выполнить по шагам.

## 1. Код

```bash
git clone https://github.com/<user>/daridrone-resilience.git
cd daridrone-resilience/stand
```

Если репозитория на GitHub ещё нет — загрузить файлы `stand/*` через редактор Killercoda.

## 2. Развернуть стенд (один раз)

```bash
kubectl create configmap code --from-file=dep.py --from-file=core.py --from-file=loadgen.py
kubectl apply -f stand.yaml
kubectl rollout status deployment/dep-a
kubectl rollout status deployment/core
kubectl get pods            # dep-a x1, core x3 (R=3) - Running
```

## 3. Эксперимент (по ~2,5 мин)

```bash
export FAULT='{"unavailable": true}'
chmod +x experiment.sh
./experiment.sh off        # without pattern
./experiment.sh on         # with pattern
```

В конце каждого прогона печатается строка метрик, например:
`POFOD=0.2500  episodes=1  ROCOF=30.0/h  AVAIL=0.7500 ...`

Дополнительно (поменять параметр):

```bash
NAME=k8s_on_maxage10 EXTRA_ENV="PLAN_MAX_AGE_S=10" ./experiment.sh on
```

## 4. Забрать результаты

```bash
ls results/                         # k8s_off.csv, k8s_on.csv, metrics_k8s_*.json, *.log
cat results/metrics_k8s_off.json    # скопировать из терминала
```

Варианты: `git add results && git commit -m "results: killercoda" && git push`, либо скопировать CSV из
терминала (`cat results/k8s_off.csv`). На ноутбуке положить файлы в `stand/results/` и выполнить
`python build_all.py --no-runs`.

## Типичные ошибки

| Симптом | Решение |
|---|---|
| `configmaps "code" already exists` | `kubectl delete configmap code` и создать снова, или `kubectl create configmap code ... --dry-run=client -o yaml \| kubectl apply -f -` |
| Поды `ContainerCreating` долго | первый раз скачивается `python:3.12-slim`, подождать 1–2 мин |
| `python3: command not found` в конце скрипта | `apt-get install -y python3` или посчитать метрики на ноутбуке: `python metrics.py results/k8s_off.csv` |
| `experiment.sh: Permission denied` | `chmod +x experiment.sh` |
| `error: timed out waiting for the condition` | `kubectl describe pod -l job-name=loadgen`, затем повторить прогон |
| Изменили `core.py`, а поды старые | пересоздать ConfigMap и `kubectl rollout restart deployment/core` |
