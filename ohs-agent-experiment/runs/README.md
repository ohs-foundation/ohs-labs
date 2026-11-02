# Runs

One folder per run, named `s1-<condition>-<model>-<replicate>`.

- **condition**: `cold`, `fhir`, `ohs` or `ohs-skills`, described in
  `../README.md`.
- **model**: the model argument given to the runner, e.g.
  `claude-opus-5-5-medium`. Gemini CLI ids have no effort suffix
  (`gemini-3.1-pro`) and Antigravity ids always do
  (`gemini-3.8-flash-medium`), so the model also tells you the agent.
  `run.json.harness` records it explicitly.
- **replicate**: `1` up.

## What a run folder holds

| File | What it is and where it comes from |
|---|---|
| `transcript.jsonl` | The agent session, the source for every metric. Claude runs copy the session file from `~/.claude/projects/<work-path>/`. Gemini and Antigravity runs capture the CLI stream-json output. |
| `transcript_full.jsonl` | Antigravity only. agy's own conversation log from `~/.gemini/antigravity-cli/brain/<conversation>/.system_generated/logs/`. The stream has no tool outputs, so build failures and `OperationOutcome` counts come from this file. |
| `transcript.md` | The same session, readable. Rendered by `extract-claude.py`, `extract-gemini.py` or `extract-antigravity.py`. |
| `run.json` | Metadata and metrics, filled by the extractor. The source of truth for the `results.csv` row. |
| `code.diff` | The agent's code changes. The work folder is committed, then diffed against the starting project. |
| `verification.json` | The automated smoke check after the build (`harness/verify.sh`). |
| `logcat.txt`, `crash.txt` | Device logs, and the crash if there was one. |
| `launch.png` | Screenshot of the app after launch and sync. |
| `global-memory-left-by-agent.md`, `knowledge-left-by-agent/` | Memory a Gemini agent tried to save globally, moved here at teardown. Kept as evidence and never fed to later runs. |

The full app source and APK of each run are in
`../harness/archive/<run_id>/`, which is not tracked in git.

## results.csv columns

`../results.csv` has one row per run, written by `harness/runner.sh`
(manual runs: `../RUNNING.md` section 4). Token counts come from the
transcript, and cost from the rate tables in `harness/extract-*.py`.

| Column | Meaning |
|---|---|
| `run_id`, `condition`, `model`, `replicate` | As in the folder name |
| `scenario` | Always `s1-build` |
| `date` | Date of the first message (empty for Antigravity runs) |
| `wall_minutes` | Time from the first to the last message |
| `corrective_turns` | User messages after the prompt. 0 for every headless run |
| `tool_calls` | Actions the agent took (commands, file edits, reads) |
| `build_failures_self_fixed` | Tool results containing `BUILD FAILED` |
| `runtime_crashes_self_fixed` | Not filled |
| `server_validation_incidents` | Tool results containing a FHIR `OperationOutcome` |
| `output_tokens`, `cache_read_tokens` | Tokens, from the transcript |
| `cost_usd_api_rates` | Cost at API prices at the time of the run |
| `kotlin_loc_added` | Lines added in `code.diff` |
| `verified_working` | The basic walk passed (register loads, a visit saves and survives a restart) |
| `round_trip_pass` | For FHIR apps, the saved visit reached the server |

The 10-check quality scores are not in `results.csv`. They are in
`../results/app-scores.md`.
