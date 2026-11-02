"""Cost and time per build by model and condition, from results.csv. Needs matplotlib.

Usage: python results/plot_charts.py
  ->  writes results/cost-by-model.png and results/minutes-by-model.png

One grouped bar chart per measure, the average of two runs, value on each bar.
Per-run detail is in results.csv and results/app-scores.md.
"""
import csv
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

HERE = Path(__file__).parent
MODELS = [
    ("gemini-3.8-flash-medium", "Gemini 3.8 Flash"),
    ("gemini-4-argon-medium", "Gemini 4 Argon"),
    ("claude-fable-5-1-medium", "Claude Fable 5.1"),
    ("claude-opus-5-5-medium", "Claude Opus 5.5"),
    ("claude-sonnet-5-5-medium", "Claude Sonnet 5.5"),
]
# Categorical slots 1-3 of the dataviz reference palette, checked for colorblind separation.
CONDITIONS = [("cold", "No FHIR", "#2a78d6"), ("ohs", "OHS", "#eb6834"),
              ("ohs-skills", "OHS + Skills", "#1baf7a")]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"

# The runs used in the blog (see ../README.md). By default cold and ohs use
# runs 1 and 2, and ohs-skills (skills v2.5) uses runs 8 and 9. Haiku never
# built a working offline app and is left out (see results/app-scores.md).
DEFAULT_RUNS = {"cold": {"1", "2"}, "ohs": {"1", "2"}, "ohs-skills": {"8", "9"}}
RUNS = {
    "gemini-3.8-flash-medium": {"ohs-skills": {"15"}},
    "gemini-4-argon-medium": {"ohs": {"2", "3"}, "ohs-skills": {"3", "4"}},
}


def used(r):
    runs = RUNS.get(r["model"], {}).get(r["condition"], DEFAULT_RUNS.get(r["condition"], set()))
    return r["replicate"] in runs


rows = [r for r in csv.DictReader(open(HERE.parent / "results.csv")) if used(r)]


def avg(model, cond, column, step):
    vals = [Decimal(r[column]) for r in rows if r["model"] == model and r["condition"] == cond]
    return (sum(vals) / len(vals)).quantize(Decimal(step), ROUND_HALF_UP)


def plot(column, step, fmt, title, out):
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.set_facecolor("#fcfcfb")
    ax.yaxis.set_major_locator(MaxNLocator(steps=[1, 2, 5, 10]))
    width = 0.26
    for i, (cond, label, color) in enumerate(CONDITIONS):
        xs = [m + (i - 1) * (width + 0.02) for m in range(len(MODELS))]
        ys = [avg(model, cond, column, step) for model, _ in MODELS]
        ax.bar(xs, [float(y) for y in ys], width, color=color, label=label)
        for x, y in zip(xs, ys):
            ax.text(x, float(y), fmt(y), ha="center", va="bottom", fontsize=10, color=INK)
    ax.set_xticks(range(len(MODELS)), [name for _, name in MODELS], fontsize=11, color=INK)
    ax.tick_params(axis="y", labelsize=10, colors=MUTED, length=0)
    ax.tick_params(axis="x", length=0)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:.2f}" if step == "0.01" else f"{v:.0f}")
    ax.grid(axis="y", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.legend(frameon=False, fontsize=11, ncols=3, loc="upper right")
    ax.set_title(title, fontsize=14, weight="bold", loc="left", color=INK, pad=14)
    fig.text(0.01, 0.01, "Average of two runs per model and condition (one run for Gemini 3.8 Flash OHS + Skills).", fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(HERE / out, dpi=150, facecolor="#fcfcfb")


plot("cost_usd_api_rates", "0.01", lambda v: f"${v}",
     "API cost per build. Skills bring OHS close to the custom app", "cost-by-model.png")
plot("wall_minutes", "0.1", lambda v: f"{v}",
     "Minutes per build. Skills bring OHS close to the custom app", "minutes-by-model.png")
