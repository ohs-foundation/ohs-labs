"""Format B: the same FHIR JSON with the noise removed (meta, narrative, extensions, identifiers).

Usage: python3 prune.py <in-dir> <out-dir>
"""
import json
import sys
from pathlib import Path

NOISE = {"meta", "text", "extension", "modifierExtension", "identifier"}


def prune(x):
    if isinstance(x, dict):
        return {k: prune(v) for k, v in x.items() if k not in NOISE}
    if isinstance(x, list):
        return [prune(v) for v in x]
    return x


def main(src, out):
    Path(out).mkdir(parents=True, exist_ok=True)
    for f in sorted(Path(src).glob("visits-*.json")):
        resources = [prune(e["resource"]) for e in json.load(open(f))["entry"]]
        (Path(out) / f.name).write_text(json.dumps(resources, separators=(",", ":")))


if __name__ == "__main__":
    main(*sys.argv[1:3])
