"""Count tokens for every format and slice with the model's own tokenizer (from the .litertlm file).

Usage: python3 count_tokens.py <model.litertlm> <data-dir> <out.csv>
Needs the LiteRT-LM Python package: pip install litert-lm
"""
import csv
import sys
from pathlib import Path

import litert_lm

FORMATS = ["A-raw", "B-pruned", "C-rows", "D-markdown"]


def main(model, data, out):
    litert_lm.set_min_log_severity(litert_lm.LogSeverity.ERROR)
    engine = litert_lm.Engine(model)
    print("context size (max_num_tokens):", engine.max_num_tokens)
    rows = []
    for fmt in FORMATS:
        for f in sorted((Path(data) / fmt).glob("visits-*")):
            text = f.read_text()
            rows.append({"format": fmt, "slice": f.stem, "chars": len(text), "tokens": len(engine.tokenize(text))})
            print(rows[-1])
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    engine.close()


if __name__ == "__main__":
    main(*sys.argv[1:4])
