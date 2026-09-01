#!/usr/bin/env python3
"""Collects one Gemini CLI eval run's artifacts, mirroring extract-claude.py:
renders transcript.md from the captured stream-json stdout, fills run.json
with the same fields, appends the same results.csv row shape.

Stream schema verified against gemini-cli v0.57.0 source (JSONL, one
event per line):
  {"type":"init", "timestamp", "session_id", "model"}
  {"type":"message", "timestamp", "role", "content", "delta"?}
  {"type":"tool_use", "timestamp", "tool_name", "tool_id", "parameters"}
  {"type":"tool_result", ...}
  {"type":"error", ...}
  {"type":"result", "timestamp", "status", "error"?, "stats": {
      "total_tokens","input_tokens","output_tokens","cached","input",
      "duration_ms","tool_calls","models":{name:{...}}}}
Falls back to defensive counting if the schema shifts in later versions.
Token pricing for Gemini models is not filled in yet - cost stays null
until GEMINI_RATES below is populated from Google's current price list.
"""

import argparse
import csv
import json
import os
import sys

# USD per million tokens (input, output), standard tier (prompts <= 200k
# tokens; Google bills a higher tier above that - costs here are therefore
# a floor for very long-context turns). Cached-token discounts are not
# applied. Gathered 2026-09-01 from public price guides; spot-check against
# ai.google.dev/pricing before quoting externally.
GEMINI_RATES = {
    # current generation (checked 2026-09-01); 3.7/3.6-flash are
    # introductory rates through 2026-12-31, then 1.50/7.50
    "gemini-3.7-flash": (0.75, 3.75),
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-3-flash": (0.50, 3.0),
    "gemini-3.1-pro": (2.0, 12.0),
    # previous generation (2.5-flash-lite retires 2026-10-16)
    "gemini-2.5-pro": (1.25, 10.0),
    "gemini-2.5-flash": (0.30, 2.50),
}


def parse_lines(path):
    events = []
    with open(path, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"_raw": line})
    return events


def walk(obj):
    """Yield every dict nested anywhere in the event."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--scenario", default="s1-build")
    ap.add_argument("--condition", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--replicate", type=int, required=True)
    ap.add_argument("--scaffold-repo", default="")
    ap.add_argument("--baseline", default="")
    ap.add_argument("--smoke", default="skip", choices=["pass", "fail", "skip"])
    ap.add_argument("--results", default="")
    ap.add_argument("--notes", default="")
    ap.add_argument("--wall-minutes", type=float, default=None)
    args = ap.parse_args()

    events = parse_lines(args.jsonl)
    os.makedirs(args.run_dir, exist_ok=True)

    # build failures and server validation incidents, counted the same way
    # the claude extractor does - from occurrences in the raw record
    raw = open(args.jsonl, errors="replace").read()
    build_failed = raw.count("BUILD FAILED")
    op_outcomes = raw.count("OperationOutcome")

    session_id = None
    model_reported = None
    tool_use_count = 0
    text_blocks = 0
    errors = 0
    final_stats = None
    final_status = None
    timestamps = []
    md = []
    assistant_buf = []

    def flush_assistant():
        nonlocal text_blocks
        if assistant_buf:
            text_blocks += 1
            md.append(f"**Agent:**\n\n{''.join(assistant_buf).strip()[:6000]}\n")
            assistant_buf.clear()

    for ev in events:
        t = ev.get("type")
        if isinstance(ev.get("timestamp"), str):
            timestamps.append(ev["timestamp"])
        if t == "init":
            session_id = ev.get("session_id") or session_id
            model_reported = ev.get("model") or model_reported
        elif t == "message":
            content = ev.get("content") or ""
            if ev.get("role") == "assistant":
                assistant_buf.append(content)   # deltas stream in chunks
            else:
                flush_assistant()
                md.append(f"---\n\n**User:**\n\n{content.strip()[:2000]}\n")
        elif t == "tool_use":
            flush_assistant()
            tool_use_count += 1
            hint = json.dumps(ev.get("parameters", {}))[:120]
            md.append(f"> tool: `{ev.get('tool_name','?')}` {hint}\n")
        elif t == "error":
            flush_assistant()
            errors += 1
            md.append(f"> error: {json.dumps(ev)[:300]}\n")
        elif t == "result":
            flush_assistant()
            final_status = ev.get("status")
            if isinstance(ev.get("stats"), dict):
                final_stats = ev["stats"]
            if isinstance(ev.get("error"), dict):
                errors += 1
                md.append(f"> result error: {json.dumps(ev['error'])[:300]}\n")
    flush_assistant()

    # authoritative numbers from the final result event when present
    tok_in = tok_out = None
    tool_calls = tool_use_count
    wall = args.wall_minutes
    if final_stats:
        tok_in = final_stats.get("input_tokens")
        tok_out = final_stats.get("output_tokens")
        if isinstance(final_stats.get("tool_calls"), int):
            tool_calls = final_stats["tool_calls"]
        if isinstance(final_stats.get("duration_ms"), (int, float)) and final_stats["duration_ms"] > 0:
            wall = round(final_stats["duration_ms"] / 60000, 1)
    if wall is None and len(timestamps) >= 2:
        from datetime import datetime
        try:
            t0 = datetime.fromisoformat(min(timestamps).replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(max(timestamps).replace("Z", "+00:00"))
            wall = round((t1 - t0).total_seconds() / 60, 1)
        except ValueError:
            pass
    args.wall_minutes = wall

    cost = None
    if args.model in GEMINI_RATES and tok_in is not None:
        in_rate, out_rate = GEMINI_RATES[args.model]
        cost = round(tok_in / 1e6 * in_rate + tok_out / 1e6 * out_rate, 2)

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
        f"condition: {args.condition} | agent: gemini-cli | model: {args.model} | "
        f"replicate: {args.replicate} | wall: {args.wall_minutes} min\n\n---\n"
    )
    with open(os.path.join(args.run_dir, "transcript.md"), "w") as f:
        f.write(header + "\n".join(md) + "\n")

    run = {
        "run_id": args.run_id,
        "scenario": args.scenario,
        "condition": args.condition,
        "model": args.model,
        "replicate": args.replicate,
        "date": None,
        "harness": "gemini-cli-headless",
        "scaffold_repo": args.scaffold_repo,
        "baseline_commit": args.baseline,
        "session_id": session_id,
        "model_reported_by_cli": model_reported,
        "final_status": final_status,
        "wall_minutes": args.wall_minutes,
        "user_turns": 1,
        "corrective_turns": 0,
        "tool_calls": tool_calls,
        "assistant_text_blocks": text_blocks,
        "tool_errors": errors,
        "build_failures_self_fixed": build_failed,
        "server_validation_incidents": op_outcomes,
        "tokens": {"input": tok_in, "output": tok_out},
        "cost_usd_api_rates": cost,
        "diff_lines_added": loc_added,
        "smoke_check": args.smoke,
        "verified_working": None,
        "round_trip_pass": None,
        "notes": (args.notes + " | schema verified against gemini-cli v0.57.0; "
                  "re-verify if the CLI is upgraded").strip(" |"),
    }
    with open(os.path.join(args.run_dir, "run.json"), "w") as f:
        json.dump(run, f, indent=2)

    if args.results:
        row = {
            "run_id": args.run_id,
            "scenario": args.scenario,
            "condition": args.condition,
            "model": args.model,
            "replicate": args.replicate,
            "date": "",
            "wall_minutes": args.wall_minutes,
            "corrective_turns": 0,
            "tool_calls": tool_calls,
            "build_failures_self_fixed": build_failed,
            "runtime_crashes_self_fixed": "",
            "server_validation_incidents": op_outcomes,
            "output_tokens": tok_out if tok_out is not None else "",
            "cache_read_tokens": "",
            "cost_usd_api_rates": cost if cost is not None else "",
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
        f"{args.run_id}: {args.wall_minutes} min, {tool_calls} tool events, "
        f"out={tok_out}, errors={errors}, smoke={args.smoke}"
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
