#!/usr/bin/env python3
"""Collects one Antigravity CLI (`agy`) eval run's artifacts, mirroring
extract-gemini.py: renders transcript.md from the captured stream-json
stdout, fills run.json with the same fields, appends the same results.csv
row shape.

Stream schema verified by probe against agy v1.2.7 (JSONL, one event per
line, compact JSON):
  {"event":"init","conversation_id","init":{"model","cwd","tools":[...],"permission_mode"}}
  {"event":"step_update","step_update":{"conversation_id","step_index","state":"ACTIVE|DONE|ERROR",
      "step_type":"user_input|agent_response|tool", "text_delta"?, "duration_seconds"?,
      "tool_name"?, "tool_info":{"name","parameters","error"?}?,
      "usage":{"input_tokens","output_tokens","thinking_tokens","cache_read_tokens","total_tokens"}?}}
  {"event":"result","result":{"conversation_id","status":"SUCCESS|...","response","duration_seconds",
      "num_turns","usage":{...},"denied_actions"?:[...]}}
A tool step emits one ACTIVE event and one DONE or ERROR event with the same
step_index; tool calls are counted from the ACTIVE events. Tool *outputs* are
not in the stream, so BUILD FAILED / OperationOutcome are counted from the
CLI's own conversation log (transcript_full.jsonl, copied by the runner) when
present, else from the stream - a floor, not an exact count.

Antigravity drives Gemini models (names like gemini-3.8-flash-low, effort
suffix always present), so pricing reuses GEMINI_RATES from
extract-gemini.py with the -low/-medium/-high suffix stripped.

Token accounting, verified on a real 217-tool-call run: `output_tokens`
already INCLUDES `thinking_tokens` (probe: output 1169 = thinking 1168 +
1 text token), and `input_tokens` EXCLUDES `cache_read_tokens` (a 15 min
run had 2.2M input vs 25M cache reads). Cost therefore bills input at the
input rate, cache reads at 0.1x the input rate (Google's cached-content
price, the same convention extract-claude.py uses), and output once.
"""

import argparse
import csv
import importlib.util
import json
import os
import sys

_GEMINI_RATES = importlib.util.spec_from_file_location(
    "extract_gemini", os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract-gemini.py")
)
_mod = importlib.util.module_from_spec(_GEMINI_RATES)
_GEMINI_RATES.loader.exec_module(_mod)
GEMINI_RATES = _mod.GEMINI_RATES

EFFORT_SUFFIXES = ("-low", "-medium", "-high")


def base_model(name):
    """gemini-3.8-flash-low -> gemini-3.8-flash (the priced model)."""
    for s in EFFORT_SUFFIXES:
        if name.endswith(s):
            return name[: -len(s)]
    return name


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

    # tool outputs live only in the CLI's own log; fall back to the stream
    full_log = os.path.join(args.run_dir, "transcript_full.jsonl")
    raw_src = full_log if os.path.exists(full_log) else args.jsonl
    raw = open(raw_src, errors="replace").read()
    build_failed = raw.count("BUILD FAILED")
    op_outcomes = raw.count("OperationOutcome")

    conversation_id = None
    model_reported = None
    permission_mode = None
    inits = 0
    results = []   # one per turn: the runner resumes the conversation when agy yields on a background task
    tool_calls = 0
    tool_errors = 0
    text_blocks = 0
    final = None
    md = []
    text_by_step = {}

    def flush_text(step_index):
        nonlocal text_blocks
        text = "".join(text_by_step.pop(step_index, [])).strip()
        if text:
            text_blocks += 1
            md.append(f"**Agent:**\n\n{text[:6000]}\n")

    for ev in events:
        kind = ev.get("event")
        if kind == "init":
            inits += 1
            conversation_id = ev.get("conversation_id") or conversation_id
            init = ev.get("init") or {}
            model_reported = init.get("model") or model_reported
            permission_mode = init.get("permission_mode")
        elif kind == "step_update":
            su = ev.get("step_update") or {}
            conversation_id = su.get("conversation_id") or conversation_id
            step_type = su.get("step_type")
            state = su.get("state")
            idx = su.get("step_index")
            if step_type == "agent_response":
                if su.get("text_delta"):
                    text_by_step.setdefault(idx, []).append(su["text_delta"])
                if state in ("DONE", "ERROR"):
                    flush_text(idx)
            elif step_type == "tool":
                info = su.get("tool_info") or {}
                if state == "ACTIVE":
                    tool_calls += 1
                    hint = json.dumps(info.get("parameters", {}))[:120]
                    md.append(f"> tool: `{su.get('tool_name', '?')}` {hint}\n")
                elif state == "ERROR":
                    tool_errors += 1
                    err = (info.get("error") or {}).get("message", "")
                    md.append(f"> tool error: {err[:300]}\n")
        elif kind == "result":
            final = ev.get("result") or {}
            results.append(final)
            conversation_id = final.get("conversation_id") or conversation_id
            if final.get("denied_actions"):
                md.append(f"> denied actions: {json.dumps(final['denied_actions'])[:300]}\n")
            if len(results) > 1:
                md.append("> harness: conversation resumed after the agent yielded on a background task\n")
    for idx in list(text_by_step):
        flush_text(idx)

    # sum usage and duration over every turn (the first prompt plus any resumes)
    def total(key):
        vals = [(r.get("usage") or {}).get(key) for r in results]
        vals = [v for v in vals if isinstance(v, (int, float))]
        return sum(vals) if vals else None
    tok = {
        "input": total("input_tokens"),
        "output": total("output_tokens"),
        "thinking": total("thinking_tokens"),
        "cache_read": total("cache_read_tokens"),
    }
    wall = args.wall_minutes
    durs = [r.get("duration_seconds") for r in results if isinstance(r.get("duration_seconds"), (int, float))]
    if durs and sum(durs) > 0:
        wall = round(sum(durs) / 60, 1)

    cost = None
    priced = base_model(args.model)
    if priced in GEMINI_RATES and tok["input"] is not None and tok["output"] is not None:
        in_rate, out_rate = GEMINI_RATES[priced]
        # output_tokens already includes thinking; cache reads are separate from input
        cost = round(
            tok["input"] / 1e6 * in_rate
            + (tok["cache_read"] or 0) / 1e6 * in_rate * 0.1
            + tok["output"] / 1e6 * out_rate,
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
        f"condition: {args.condition} | agent: antigravity-cli | model: {args.model} | "
        f"replicate: {args.replicate} | wall: {wall} min\n\n---\n"
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
        "harness": "antigravity-cli-headless",
        "scaffold_repo": args.scaffold_repo,
        "baseline_commit": args.baseline,
        "session_id": conversation_id,
        "model_reported_by_cli": model_reported,
        "permission_mode": permission_mode,
        "final_status": (final or {}).get("status"),
        "resume_turns": max(0, inits - 1),
        "wall_minutes": wall,
        "user_turns": 1,
        "corrective_turns": 0,
        "tool_calls": tool_calls,
        "assistant_text_blocks": text_blocks,
        "tool_errors": tool_errors,
        "build_failures_self_fixed": build_failed,
        "server_validation_incidents": op_outcomes,
        "tokens": tok,
        "cost_usd_api_rates": cost,
        "diff_lines_added": loc_added,
        "smoke_check": args.smoke,
        "verified_working": None,
        "round_trip_pass": None,
        "notes": (
            args.notes
            + " | schema verified against agy v1.2.7; re-verify if the CLI is upgraded"
            + ("" if os.path.exists(full_log) else " | no transcript_full.jsonl: build/validation counts are from the stream only")
        ).strip(" |"),
    }
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
            "model": args.model,
            "replicate": args.replicate,
            "date": "",
            "wall_minutes": wall,
            "corrective_turns": 0,
            "tool_calls": tool_calls,
            "build_failures_self_fixed": build_failed,
            "runtime_crashes_self_fixed": "",
            "server_validation_incidents": op_outcomes,
            "output_tokens": tok["output"] if tok["output"] is not None else "",
            "cache_read_tokens": tok["cache_read"] if tok["cache_read"] is not None else "",
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
        f"{args.run_id}: {wall} min, {tool_calls} tool calls, "
        f"out={tok['output']}, tool_errors={tool_errors}, smoke={args.smoke}"
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
