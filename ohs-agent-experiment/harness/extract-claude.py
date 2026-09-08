#!/usr/bin/env python3
"""Collects one eval run's artifacts: renders transcript.md from the session
jsonl, fills run.json with metrics, appends the results.csv row.

Usage:
  extract-claude.py --jsonl PATH --run-dir runs/<run_id> --run-id ID \
             --scenario s1-build --condition cold|ohs|ohs-skills \
             --model fable|sonnet|haiku --replicate N \
             --scaffold-repo NAME --baseline COMMIT \
             [--smoke pass|fail|skip] [--results results.csv] [--notes TEXT]
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

MODEL_IDS = {
    "fable": "claude-fable-5",
    "sonnet": "claude-sonnet-5",
    "opus": "claude-opus-5",
    "haiku": "claude-haiku-4-5-20251001",
}
# USD per million tokens: input, output. Cache read = 0.1x input,
# cache write = 1.25x input (5-minute tier).
RATES = {
    "fable": (10.0, 50.0),
    "sonnet": (2.0, 10.0),
    "opus": (5.0, 25.0),
    "haiku": (1.0, 5.0),
}


def parse(jsonl_path):
    events = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ).strip()
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--scenario", default="s1-build")
    ap.add_argument("--condition", required=True)
    ap.add_argument("--model", required=True, choices=MODEL_IDS)
    ap.add_argument("--replicate", type=int, required=True)
    ap.add_argument("--scaffold-repo", default="")
    ap.add_argument("--baseline", default="")
    ap.add_argument("--smoke", default="skip", choices=["pass", "fail", "skip"])
    ap.add_argument("--results", default="")
    ap.add_argument("--notes", default="")
    ap.add_argument("--wall-minutes", type=float, default=None,
                    help="fallback wall clock from the runner; session timestamps win")
    args = ap.parse_args()

    events = parse(args.jsonl)
    os.makedirs(args.run_dir, exist_ok=True)

    ts, session_id = [], None
    user_turns, corrective_candidates = 0, 0
    tool_calls, asst_blocks = 0, 0
    build_failed, op_outcomes, tool_errors = 0, 0, 0
    tok = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    md = []

    for d in events:
        if d.get("timestamp"):
            ts.append(d["timestamp"])
        session_id = d.get("sessionId") or session_id
        kind = d.get("type")

        if kind == "assistant":
            m = d.get("message", {})
            u = m.get("usage") or {}
            tok["input"] += u.get("input_tokens", 0)
            tok["output"] += u.get("output_tokens", 0)
            tok["cache_read"] += u.get("cache_read_input_tokens", 0)
            tok["cache_write"] += u.get("cache_creation_input_tokens", 0)
            for b in m.get("content", []):
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and b.get("text", "").strip():
                    asst_blocks += 1
                    md.append(f"**Assistant:**\n\n{b['text'].strip()}\n")
                elif b.get("type") == "tool_use":
                    tool_calls += 1
                    name = b.get("name", "?")
                    inp = b.get("input", {})
                    hint = (
                        inp.get("command")
                        or inp.get("file_path")
                        or inp.get("description")
                        or ""
                    )
                    hint = " ".join(str(hint).split())[:120]
                    md.append(f"> tool: `{name}` {hint}\n")

        elif kind == "user" and not d.get("isMeta"):
            c = d.get("message", {}).get("content")
            body = text_of(c)
            if body:
                user_turns += 1
                if user_turns > 1:
                    corrective_candidates += 1
                md.append(f"---\n\n**User:**\n\n{body}\n")
            if isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        s = (
                            b["content"]
                            if isinstance(b.get("content"), str)
                            else json.dumps(b.get("content", ""))
                        )
                        if b.get("is_error"):
                            tool_errors += 1
                        if "BUILD FAILED" in s:
                            build_failed += 1
                        if "OperationOutcome" in s:
                            op_outcomes += 1

    wall_minutes = args.wall_minutes
    if ts:
        try:
            t0 = datetime.fromisoformat(min(ts).replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(max(ts).replace("Z", "+00:00"))
            wall_minutes = round((t1 - t0).total_seconds() / 60, 1)
        except ValueError:
            pass

    in_rate, out_rate = RATES[args.model]
    cost = round(
        tok["input"] / 1e6 * in_rate
        + tok["output"] / 1e6 * out_rate
        + tok["cache_read"] / 1e6 * in_rate * 0.1
        + tok["cache_write"] / 1e6 * in_rate * 1.25,
        2,
    )

    loc_added = None
    diff_path = os.path.join(args.run_dir, "code.diff")
    if os.path.exists(diff_path):
        loc_added = 0
        with open(diff_path, errors="replace") as f:
            for line in f:
                if line.startswith("+") and not line.startswith("+++"):
                    loc_added += 1

    header = (
        f"# {args.run_id}\n\n"
        f"condition: {args.condition} | model: {MODEL_IDS[args.model]} | "
        f"replicate: {args.replicate} | wall: {wall_minutes} min | "
        f"cost (API rates): ${cost}\n\n---\n"
    )
    with open(os.path.join(args.run_dir, "transcript.md"), "w") as f:
        f.write(header + "\n".join(md) + "\n")

    run = {
        "run_id": args.run_id,
        "scenario": args.scenario,
        "condition": args.condition,
        "model": MODEL_IDS[args.model],
        "replicate": args.replicate,
        "date": (min(ts)[:10] if ts else None),
        "harness": "claude-code-headless",
        "scaffold_repo": args.scaffold_repo,
        "baseline_commit": args.baseline,
        "session_id": session_id,
        "wall_minutes": wall_minutes,
        "user_turns": user_turns,
        "corrective_turns": corrective_candidates,
        "tool_calls": tool_calls,
        "assistant_text_blocks": asst_blocks,
        "tool_errors": tool_errors,
        "build_failures_self_fixed": build_failed,
        "server_validation_incidents": op_outcomes,
        "tokens": tok,
        "cost_usd_api_rates": cost,
        "diff_lines_added": loc_added,
        "smoke_check": args.smoke,
        "verified_working": None,  # human walk fills this in
        "round_trip_pass": None,
        "notes": args.notes,
    }
    # fold in verify.sh's automated end-to-end result if present
    _vpath = os.path.join(args.run_dir, "verification.json")
    if os.path.exists(_vpath):
        try:
            run["verification"] = json.load(open(_vpath))
        except Exception:
            pass

    with open(os.path.join(args.run_dir, "run.json"), "w") as f:
        json.dump(run, f, indent=2)

    if args.results:
        row = {
            "run_id": args.run_id,
            "scenario": args.scenario,
            "condition": args.condition,
            "model": MODEL_IDS[args.model],
            "replicate": args.replicate,
            "date": run["date"],
            "wall_minutes": wall_minutes,
            "corrective_turns": corrective_candidates,
            "tool_calls": tool_calls,
            "build_failures_self_fixed": build_failed,
            "runtime_crashes_self_fixed": "",
            "server_validation_incidents": op_outcomes,
            "output_tokens": tok["output"],
            "cache_read_tokens": tok["cache_read"],
            "cost_usd_api_rates": cost,
            "kotlin_loc_added": loc_added,
            "verified_working": "",
            "round_trip_pass": "",
        }
        exists = os.path.exists(args.results)
        with open(args.results, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            if not exists:
                w.writeheader()
            w.writerow(row)

    print(
        f"{args.run_id}: {wall_minutes} min, {tool_calls} tool calls, "
        f"${cost}, out={tok['output']:,}, smoke={args.smoke}"
    )
    missing = [
        n
        for n in ("transcript.jsonl", "transcript.md", "run.json", "code.diff")
        if not os.path.exists(os.path.join(args.run_dir, n))
    ]
    if missing:
        print(f"INCOMPLETE - missing: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
