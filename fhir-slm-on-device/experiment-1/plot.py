"""Chart for experiment 1: prompt tokens per format as the record grows, against context sizes.

Usage: python3 plot.py   (needs matplotlib)  ->  results/tokens-by-format.png
"""
import csv
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).parent
FORMATS = [("A-raw", "A raw FHIR JSON", "#2a78d6"), ("B-pruned", "B pruned JSON", "#eb6834"),
           ("C-rows", "C SQL-on-FHIR rows", "#1baf7a"), ("D-markdown", "D Tokempic markdown", "#7d5ba6")]
CONTEXTS = [(4096, "4K default"), (8192, "8K"), (16384, "16K"), (32768, "32K")]

rows = list(csv.DictReader(open(HERE / "results/tokens.csv")))
fig, ax = plt.subplots(figsize=(10, 5.5))
for key, label, color in FORMATS:
    pts = [(int(r["slice"].split("-")[1]), int(r["tokens"])) for r in rows if r["format"] == key]
    ax.plot(*zip(*pts), marker="o", linewidth=2, color=color, label=label)
for n, label in CONTEXTS:
    ax.axhline(n, color="#9a9893", linewidth=1, linestyle="--")
    ax.text(1.01, n, f"{label} context", va="center", fontsize=9, color="#52514e",
            transform=ax.get_yaxis_transform())
ax.set_yscale("log")
ax.set_xlabel("Visits in the record")
ax.set_ylabel("Prompt tokens (log scale)")
ax.set_title("Prompt tokens per format as the record grows (Gemma 4 E2B tokenizer)", loc="left", weight="bold")
ax.grid(axis="y", color="#e6e5e1")
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, loc="upper left")
fig.tight_layout(rect=(0, 0, 0.9, 1))
fig.savefig(HERE / "results/tokens-by-format.png", dpi=150)
