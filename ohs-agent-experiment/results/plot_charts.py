"""Cost and time per run by model and condition, from results.csv. Needs matplotlib.

Usage: python results/plot_charts.py
  ->  writes results/cost-by-model.png and results/minutes-by-model.png
"""
import csv
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

HERE = Path(__file__).parent
MODELS = [
    ("gemini-3.8-flash-medium", "Gemini 3.8 Flash"),
    ("claude-fable-5-1-medium", "Claude Fable 5.1"),
    ("claude-opus-5-5-medium", "Claude Opus 5.5"),
    ("claude-sonnet-5-5-medium", "Claude Sonnet 5.5"),
    ("claude-haiku-5-5-medium", "Claude Haiku 5.5"),
]
CONDITIONS = [("cold", "Cold"), ("ohs", "OHS"), ("ohs-skills", "OHS +\nSkills")]
COLORS = {"cold": "#9aa5b1", "ohs": "#e07a5f", "ohs-skills": "#3d8bfd"}
# Apps that failed the emulator walk or keep nothing on the device
# (results/walk-claude-2026-10.md).
FAILED = {
    ("claude-haiku-5-5-medium", "ohs"), ("claude-haiku-5-5-medium", "ohs-skills"),
    ("claude-sonnet-5-5-medium", "ohs"),
}

rows = list(csv.DictReader(open(HERE.parent / "results.csv")))


def plot(column, fmt, ylabel, title, out):
    fig, axes = plt.subplots(1, len(MODELS), figsize=(15, 4.2), sharey=True)
    top = max(float(r[column]) for r in rows)
    for ax, (model, name) in zip(axes, MODELS):
        for i, (cond, _) in enumerate(CONDITIONS):
            vals = [float(r[column]) for r in rows
                    if r["model"] == model and r["condition"] == cond]
            avg = sum(vals) / len(vals)
            label = (sum(Decimal(str(v)) for v in vals) / len(vals)).quantize(
                Decimal("0.01" if fmt == "$" else "0.1"), ROUND_HALF_UP)
            ax.bar(i, avg, color=COLORS[cond], width=0.65)
            ax.text(i, max(vals) + top * 0.02, f"${label}" if fmt == "$" else f"{label}",
                    ha="center", va="bottom", fontsize=9, weight="bold")
            failed = (model, cond) in FAILED
            ax.scatter([i - 0.12, i + 0.12], vals, zorder=3, s=28,
                       marker="x" if failed else "o",
                       color="#c0392b" if failed else "#222")
        ax.set_title(name, fontsize=11)
        ax.set_xticks(range(len(CONDITIONS)), [c[1] for c in CONDITIONS], fontsize=9)
        ax.yaxis.set_major_formatter(
            (lambda v, _: f"${v:.2f}") if fmt == "$" else (lambda v, _: f"{v:.0f}"))
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylim(0, top * 1.1)
    if fmt != "$":
        axes[0].yaxis.set_major_locator(MultipleLocator(5))
    axes[0].set_ylabel(ylabel)
    fig.suptitle(title, fontsize=13, weight="bold")
    fig.text(0.5, 0.01, "Bar = average of two runs. Dot = one run. Red x = app failed.",
             ha="center", fontsize=9, color="#555")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(HERE / out, dpi=150)


plot("cost_usd_api_rates", "$", "API cost per run",
     "Skills bring the cost of building on FHIR close to a custom app", "cost-by-model.png")
plot("wall_minutes", "min", "Minutes per run",
     "Time to finish follows the same pattern", "minutes-by-model.png")
