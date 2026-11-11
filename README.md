# DäriDrone — экзаменационный проект, вариант 5

**Software Resilience and Risk Assessment** · Astana IT University · SSE-2502
Студент A: Айкенов Ерасыл · Студент B: `<ФИО партнёра>`

Система: доставка лекарств дронами. Ключевая функция — **контроль полёта** (RTO 1 мин, RPO 0).
Паттерн в коде — **static stability: полётный план в памяти**. Отказ в эксперименте — **R=3 · dep-a недоступна (503)**.

## Что где лежит

| Путь | Что |
|---|---|
| `report/report.pdf` | Отчёт (задания 1–8 + практика) |
| `stand/core.py` | Сервис контроля полёта, паттерн — функции `refresh_plan()` и `do_work()` |
| `stand/test_core.py`, `stand/test_metrics.py` | 13 тестов (8 паттерна + 5 метрик) |
| `stand/metrics.py` | POFOD, эпизоды, ROCOF, AVAIL, p50/p95/p99 из CSV |
| `stand/dep.py`, `stand/loadgen.py` | Диспетчер (dep-a) и «дроны» (нагрузка) |
| `stand/stand.yaml`, `stand/load-job.yaml`, `stand/experiment.sh` | Прогон в Kubernetes |
| `stand/run_local.py` | Тот же прогон без кластера (процессы на 127.0.0.1) |
| `stand/results/` | CSV, логи, JSON метрик, `HYPOTHESIS.md` |
| `analysis/calc.py` | Расчёты заданий 3–6 → `analysis/results.json` |
| `analysis/figures.py` | Рисунки → `report/figures/` |
| `k8s-plan/flight-control.yaml` | Задание 7: Deployment, PDB, HPA, probes |
| `show_results.py` | Итоговая таблица в терминале |
| `screenshots/` | Скриншоты, снятые на ноутбуке |
| `DEMO.md` | Шпаргалка к защите |
| `KILLERCODA.md` | Прогон в Killercoda |
| `ASSUMPTIONS.md` | Допущения |

## Быстрый старт (Windows PowerShell или bash)

```bash
cd stand && python -m unittest -v && cd ..     # 13 tests OK
python analysis/calc.py                         # tasks 3-6, control values
python show_results.py                          # final table: given / off / on
```

Повторить эксперимент локально (по 2 минуты): `cd stand; python run_local.py off; python run_local.py on`.
Пересобрать всё (тесты → прогоны → расчёты → рисунки → PDF): `python build_all.py` (≈ 12 мин) или
`python build_all.py --no-runs` (без новых прогонов, ≈ 1 мин).

## Источник цифр

* **Локальный прогон** — процессы на ноутбуке (`run_local.py`).
* **Kubernetes** — кластер kind внутри Docker Desktop на этом же ноутбуке, `experiment.sh`, core R=3.
* В Killercoda — тот же `experiment.sh` (см. `KILLERCODA.md`); положить CSV в `stand/results/` и выполнить
  `python build_all.py --no-runs` — таблица, графики и отчёт пересчитаются.

## Git

Репозиторий локальный. Чтобы выложить на GitHub:

```bash
gh repo create daridrone-resilience --private --source . --push
# или: git remote add origin https://github.com/<user>/daridrone-resilience.git && git push -u origin main
```
