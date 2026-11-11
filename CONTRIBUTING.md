# Как мы работаем

* `main` — только проверенный код; прямые коммиты в `main` не делаем.
* Студент A работает в `feature/pattern-static-stability` (core.py, test_core.py), студент B — в `feature/metrics` (metrics.py, test_metrics.py, прогоны).
* Каждая ветка вливается через pull request; ревью делает партнёр: запускает `cd stand && python -m unittest -v` и проверяет, что цифры в отчёте совпадают с `python show_results.py`.
* Сообщения коммитов — Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
* Каждый коммитит под своим именем — у партнёра свои коммиты в истории.
