"""Collect experiment 1 numbers into one table per slice: resources, tokens per format, and device runs.

Usage: python3 summarize.py  ->  results/summary.csv and a markdown table on stdout
"""
import collections
import csv
import json
import statistics
from pathlib import Path

HERE = Path(__file__).parent
tokens = {(r["format"], r["slice"]): int(r["tokens"]) for r in csv.DictReader(open(HERE / "results/tokens.csv"))}
# Device runs made with run_device.sh (prompt names like D-markdown_visits-05.md). When a slice
# was run with several context sizes, keep the smallest, which is the one sized to the prompt.
# When it was run more than once at that size, keep the run with the median total time.
by_slice = collections.defaultdict(list)
for line in open(HERE / "results/device-runs.txt"):
    if line.startswith("prompt=") and "error=" not in line:
        kv = dict(p.split("=", 1) for p in line.split())
        fmt, _, name = kv["prompt"].partition("_")
        if name:
            by_slice[(fmt, Path(name).stem)].append(kv)
runs = {}
for key, kvs in by_slice.items():
    smallest = min(int(kv["max_tokens"]) for kv in kvs)
    same = sorted((kv for kv in kvs if int(kv["max_tokens"]) == smallest), key=lambda kv: int(kv["total_ms"]))
    runs[key] = same[len(same) // 2]

rows = []
for f in sorted((HERE / "data/A-raw").glob("visits-*.json")):
    resources = [e["resource"] for e in json.load(open(f))["entry"]]
    types = collections.Counter(r["resourceType"] for r in resources)
    visits = int(f.stem.split("-")[1])
    row = {
        # A slice is the last N visits plus anything they point to, which can pull in an older Encounter.
        "slice": f.stem, "visits": visits, "encounters": types["Encounter"], "resources": len(resources),
        "resources_per_visit": round(len(resources) / visits, 1),
        "observations": types["Observation"], "conditions": types["Condition"], "procedures": types["Procedure"],
        **{f"tokens_{k}": tokens[(k, f.stem)] for k in ("A-raw", "B-pruned", "C-rows", "D-markdown")},
    }
    run = runs.get(("D-markdown", f.stem))
    if run:
        row.update({
            "D_context": run["max_tokens"], "D_input_tokens": run["prefill_tokens"],
            "D_output_tokens": run["decode_tokens"], "D_load_s": round(int(run["load_ms"]) / 1000, 1), "D_ttft_s": round(int(run["ttft_ms"]) / 1000, 1),
            "D_total_s": round(int(run["total_ms"]) / 1000, 1), "D_prefill_tps": run["prefill_tps"],
            "D_decode_tps": run["decode_tps"], "D_peak_mb": run["peak_rss_mb"],
        })
    rows.append(row)

# How many resources a single visit has, across the whole record.
full = json.load(open(HERE / "data/A-raw/visits-51.json"))["entry"]
per_visit = collections.Counter(e["resource"]["encounter"]["reference"] for e in full if "encounter" in e["resource"])
counts = sorted(per_visit.values())
print(f"Resources recorded at one visit: min {counts[0]}, median {statistics.median(counts)}, max {counts[-1]}")

keys = list(dict.fromkeys(k for r in rows for k in r))
with open(HERE / "results/summary.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)
print("| " + " | ".join(keys) + " |")
print("|" + "---|" * len(keys))
for r in rows:
    print("| " + " | ".join(str(r.get(k, "")) for k in keys) + " |")
