"""Figures for the report: risk matrix 5x5, stand charts, architecture, DFD.

python analysis/figures.py   -> report/figures/*.png
"""
import csv
import json
import math
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "stand", "results")
OUT = os.path.join(ROOT, "report", "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

RED, ORANGE, GREEN = "#e06666", "#f6b26b", "#93c47d"
OFF_C, ON_C, AGE_C = "#cc0000", "#1c7c54", "#3d85c6"


def risk_matrix(risks):
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    cells = defaultdict(list)
    for r in risks:
        cells[(r["p"], r["i"])].append(r["id"])
    for p in range(1, 6):
        for i in range(1, 6):
            s = p * i
            color = RED if s >= 15 else (ORANGE if s >= 8 else GREEN)
            ax.add_patch(Rectangle((i - 0.5, p - 0.5), 1, 1, facecolor=color, edgecolor="white", lw=2))
            ax.text(i - 0.42, p + 0.32, str(s), fontsize=8, color="#444")
            if cells[(p, i)]:
                ax.text(i, p - 0.05, "\n".join(cells[(p, i)]) if len(cells[(p, i)]) < 3
                        else ", ".join(cells[(p, i)][:2]) + "\n" + ", ".join(cells[(p, i)][2:]),
                        ha="center", va="center", fontsize=10, fontweight="bold")
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.set_xlabel("Воздействие →")
    ax.set_ylabel("Вероятность →")
    ax.set_title("Матрица рисков 5×5 (DäriDrone)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=RED, label="15–25 критический"),
                       Patch(color=ORANGE, label="8–14 высокий/средний"),
                       Patch(color=GREEN, label="1–7 низкий")],
              loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "risk_matrix.png"), dpi=160)
    plt.close(fig)


def per_second(path):
    ok, total, lat = defaultdict(int), defaultdict(int), defaultdict(list)
    with open(path) as f:
        for r in csv.DictReader(f):
            s = math.floor(float(r["t"]))
            total[s] += 1
            ok[s] += int(r["status"]) == 200
            lat[s].append(float(r["latency_ms"]))
    secs = sorted(total)
    return secs, [ok[s] / total[s] for s in secs], [sorted(lat[s])[len(lat[s]) // 2] for s in secs]


def experiment_chart(runs, title, fname):
    runs = [(lbl, os.path.join(RES, f), c, ls) for lbl, f, c, ls in runs if os.path.exists(os.path.join(RES, f))]
    if not runs:
        return False
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.6), sharex=True)
    for ax in (a1, a2):
        ax.axvspan(30, 60, color="#f4cccc", alpha=0.6, lw=0)
        ax.grid(alpha=0.3)
    for lbl, path, c, ls in runs:
        secs, ok, med = per_second(path)
        a1.plot(secs, ok, color=c, ls=ls, lw=1.8, label=lbl)
        a2.plot(secs, med, color=c, ls=ls, lw=1.8, label=lbl)
    a1.set_ylabel("Доля ответов 200")
    a1.set_ylim(-0.05, 1.1)
    a1.text(45, 0.5, "dep-a: 503\n(30–60 с)", ha="center", fontsize=9, color="#990000")
    a1.legend(loc="lower left", fontsize=8)
    a1.set_title(title)
    a2.set_ylabel("Медиана задержки, мс")
    a2.set_yscale("log")
    a2.set_xlabel("Время от начала прогона, с")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname), dpi=160)
    plt.close(fig)
    return True


def box(ax, x, y, w, h, text, color="#d9e8f5", ec="#33658a", bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor=color, edgecolor=ec, lw=1.5))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.5,
            fontweight="bold" if bold else "normal")


def arrow(ax, x1, y1, x2, y2, text="", color="#333"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4))
    if text:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, text, ha="center", va="bottom",
                fontsize=7.5, color=color, bbox=dict(facecolor="white", edgecolor="none", pad=0.5))


def architecture():
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    spof = "#fce5cd"
    box(ax, 0.1, 3.6, 1.8, 0.9, "Приложение\nклиники / аптеки")
    box(ax, 2.4, 3.6, 1.8, 0.9, "API заказов")
    box(ax, 4.7, 3.6, 2.2, 0.9, "A: Диспетчерская\nFlight Control API\n(1 сервер)", spof, "#b45f06", True)
    box(ax, 4.7, 1.9, 2.2, 0.9, "B: БД полётных\nпланов и телеметрии\n(1 сервер)", spof, "#b45f06", True)
    box(ax, 2.4, 1.9, 1.8, 0.9, "Планировщик\nмаршрутов")
    box(ax, 0.1, 1.9, 1.8, 0.9, "Сервис погоды /\nUTM (внешний)", "#eeeeee", "#666")
    box(ax, 7.5, 3.6, 2.3, 0.9, "C: Канал LTE\nсотового оператора\n(внешний, SLA 0,993)", spof, "#b45f06", True)
    box(ax, 7.5, 1.4, 2.3, 1.2, "Бортовой полётный\nконтроллер дрона\n(план в памяти —\nstatic stability)", "#d9ead3", "#38761d", True)
    arrow(ax, 1.9, 4.05, 2.4, 4.05)
    arrow(ax, 4.2, 4.05, 4.7, 4.05)
    arrow(ax, 6.9, 4.05, 7.5, 4.05)
    arrow(ax, 8.65, 3.6, 8.65, 2.6, "команды /\nтелеметрия")
    arrow(ax, 5.8, 3.6, 5.8, 2.8)
    arrow(ax, 3.3, 2.8, 4.7, 3.7)
    arrow(ax, 1.9, 2.35, 2.4, 2.35)
    ax.text(0.1, 0.6, "Оранжевым — единые точки отказа (SPOF) в исходной архитектуре. "
                      "Зелёным — борт, который продолжает полёт по плану в памяти.",
            fontsize=8, color="#444")
    ax.set_title("Архитектура DäriDrone (задание 2)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "architecture.png"), dpi=160)
    plt.close(fig)


def dfd():
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    for x, w, lbl in [(0.05, 1.9, "Граница: дрон"), (2.2, 1.8, "Граница: сеть оператора"),
                      (4.25, 3.4, "Граница: ЦОД диспетчерской"), (7.9, 2.05, "Граница: клиника")]:
        ax.add_patch(Rectangle((x, 0.5), w, 3.6, fill=False, ls="--", ec="#cc0000", lw=1.2))
        ax.text(x + 0.05, 3.95, lbl, fontsize=7.5, color="#cc0000")
    box(ax, 0.2, 1.8, 1.6, 1.0, "Процесс:\nполётный\nконтроллер")
    box(ax, 2.35, 1.8, 1.5, 1.0, "Поток:\nканал LTE C2", "#eeeeee", "#666")
    box(ax, 4.4, 2.5, 1.6, 1.0, "Процесс:\nFlight Control\nAPI")
    box(ax, 4.4, 0.8, 1.6, 0.9, "Хранилище:\nБД планов", "#fff2cc", "#bf9000")
    box(ax, 6.2, 2.5, 1.3, 1.0, "Внешн.:\nоператор\nдиспетчер")
    box(ax, 8.1, 1.8, 1.7, 1.0, "Внешн.:\nприложение\nклиники")
    arrow(ax, 1.8, 2.45, 2.35, 2.45, "S,T,D")
    arrow(ax, 3.85, 2.45, 4.4, 2.8, "S,T,D")
    arrow(ax, 5.2, 2.5, 5.2, 1.7, "T,I")
    arrow(ax, 6.2, 3.0, 6.0, 3.0, "E")
    arrow(ax, 8.1, 2.3, 6.0, 2.7, "S,R")
    ax.set_title("DFD с границами доверия и угрозами STRIDE (задание 6)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "dfd.png"), dpi=160)
    plt.close(fig)


def main():
    with open(os.path.join(ROOT, "analysis", "results.json"), encoding="utf-8") as f:
        risks = json.load(f)["risks"]
    risk_matrix(risks)
    architecture()
    dfd()
    experiment_chart([("PATTERN=off", "off.csv", OFF_C, "-"),
                      ("PATTERN=on", "on.csv", ON_C, "-"),
                      ("PATTERN=on, PLAN_MAX_AGE_S=10", "on_maxage10.csv", AGE_C, "--")],
                     "Локальный прогон: dep-a недоступна (503) с 30 по 60 с", "experiment_local.png")
    experiment_chart([("PATTERN=off (Kubernetes)", "k8s_off.csv", OFF_C, "-"),
                      ("PATTERN=on (Kubernetes)", "k8s_on.csv", ON_C, "-")],
                     "Kubernetes (kind в Docker, core R=3): dep-a 503 с 30 по 60 с", "experiment_k8s.png")
    for f in sorted(os.listdir(OUT)):
        print(f"figure: report/figures/{f}")


if __name__ == "__main__":
    main()
