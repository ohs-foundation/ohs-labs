# Runs

One folder per run: `s<scenario>-<condition>-<model>-<replicate>`.

- **scenario**: `s1` build; `s2a` form update, `s2b` data export, `s2c` bad
  record (Part 2 demonstrations, one replicate only).
- **condition**: `cold` (scratch), `ohs` (Foundations libraries), `ohs-skills`
  (Foundations + `ohs-agent-experiment/skills/` in `.claude/skills/`).
- **model**: `fable`, `sonnet`, `haiku` (add e.g. `gemini` for cross-agent runs).
- **replicate**: two digits, `01` up.

Each folder holds: `transcript.jsonl` (required), `transcript.md` (export,
optional), `run.json` (metadata + metrics), `code.diff` (vs the scaffold's
baseline commit), `recording.mov` (if captured).

`../results.csv` carries one row per run and is the only file analysis
reads. After a run: copy the session jsonl in, fill `run.json`, append the
CSV row. Token counts come from the jsonl usage fields; cost at the model's
API rates (see ../docs/protocol.md).

Per-run scaffold hygiene: run in the condition's scaffold repo, then
`git add -A && git commit -m "<run_id>" && git tag <run_id>` and
`git reset --hard <baseline>` to ready it for the next run. The tag keeps
the full code; `code.diff` here is the greppable copy.
