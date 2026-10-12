# Runs

One folder per run: `s<scenario>-<condition>-<model>-<replicate>`.

- **scenario**: `s1` build; `s2a` form update, `s2b` data export, `s2c` bad
  record (Part 2 demonstrations, one replicate only).
- **condition**: `cold` (scratch), `ohs` (Foundations libraries), `ohs-skills`
  (Foundations + `ohs-agent-experiment/skills/`, placed where each agent
  loads them: `.claude/skills/`, `.agents/skills/`, or one `GEMINI.md`).
- **model**: `fable`, `opus`, `sonnet`, `haiku` (Claude); cross-agent runs use that agent's model names (e.g. `gemini-3.1-pro` for Gemini CLI, `gemini-3.8-flash-low` for Antigravity CLI, whose ids always carry an effort suffix) - the model segment implies the agent, and `run.json.harness` records it explicitly. No per-agent subfolders: one runs/ tree, one results.csv.
- **replicate**: two digits, `01` up.

Each folder holds: `transcript.jsonl` (required), `transcript.md`,
`run.json` (metadata + metrics), `code.diff` (vs the scaffold's baseline
commit), `verification.json`, `logcat.txt`, `crash.txt` (if it crashed),
`launch.png` / `recording.mov` (if captured), and for gemini
runs possibly `global-memory-left-by-agent.md` (quarantined global
memory the agent tried to save - kept as evidence, never fed to later
runs). Antigravity runs add `transcript_full.jsonl` (agy's own
conversation log, the only place tool outputs appear) and possibly
`knowledge-left-by-agent/` (quarantined knowledge-store writes).

`../results.csv` carries one row per run and is the only file analysis
reads. `harness/runner.sh` fills the folder and appends the row; manual
runs follow `../RUNNING.md` section 5. Token counts come from the
transcript; cost uses the rates tables in `harness/extract-*.py`. The
full code of each run is kept in `harness/archive/<run_id>/` (not
tracked); `code.diff` here is the greppable copy.
