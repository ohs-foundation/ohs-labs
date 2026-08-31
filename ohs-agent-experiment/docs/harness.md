# Harness design

Why the run automation is shaped the way it is: the grid, the per-run
cleanliness contract, and the failure policy. The step-by-step of what a
run actually does lives in `../RUNNING.md`; the protocol it implements is
`protocol.md` Part B.

## The grid

Skills only make sense on the OHS build, so the grid is 12 cells:

| | fable | opus | sonnet | haiku |
|---|---|---|---|---|
| **cold** (scratch) | x | x | x | x |
| **ohs** (Foundations) | x | x | x | x |
| **ohs-skills** (Foundations + `skills/`) | x | x | x | x |

Replicates: **N=3 per cell** (stretch: 5 for the cells that decide claims —
haiku rows and the ohs vs ohs-skills fable pair). Run order: **one full
sweep of all 9 cells first** (early signal on every claim), then the
remaining replicates interleaved, not cell-by-cell (spreads time-of-day and
flakiness evenly).


## Cleanliness contract (the heart of this)

Every run must start with zero trace of any previous run, across five kinds
of state:

| State | Contamination risk | How it's cleaned | Verified by |
|---|---|---|---|
| **Agent context** | resumed session, project auto-memory, session history | **fresh directory per run** (`work/<run_id>/`, cloned from the condition's baseline): a new path means a new Claude Code project — empty session history, empty memory | runner asserts `~/.claude/projects/<dashed-path>/` doesn't pre-exist |
| **Agent instructions** | user-level `~/.claude/CLAUDE.md`, global settings | audit once before the campaign: no user-level CLAUDE.md content that could coach the runs; global config is then *constant across all cells*, so comparisons stay valid | manual check, noted in campaign log |
| **Server state** | previous run's uploaded resources, watermarks | `docker-compose down` (destroys in-container H2) then `up -d` + `load-seed.sh` before **every** run, including cold runs (constant environment) | seed script's resource-count check (3/3/12/1) |
| **App/device state** | installed APKs, on-device databases, sync work queues | uninstall sweep: `adb shell pm list packages com.example | ...uninstall`; if a run installed anything unexpected, cold-boot the AVD with `-wipe-data` | runner asserts no `com.example.*` packages before start |
| **Build caches** | first run pays dependency downloads, later runs don't (skews wall-clock and possibly turns) | keep Gradle caches **warm for everyone**: before the campaign, run one throwaway `assembleDebug` per scaffold flavor; caches are then uniformly warm — a constant, not a variable | throwaway builds logged in campaign log |

The fresh-directory-per-run rule does the heaviest lifting: it kills session
resume, auto-memory bleed, and stale git state in one move, and makes the
scheme parallel-safe later if we ever want it.

One more filesystem rule: **no interesting siblings.** With
bypassPermissions an agent could `ls ..` into a previous run's work dir and
find a finished solution. So after collection, each run's work dir is moved
out of `work/` (archived beside its `runs/` folder or deleted); the runner
asserts `work/` contains only the current run before starting. The model
itself carries nothing between sessions - there is no server-side memory of
past conversations - so with the directory channels closed, the only
knowledge injection anywhere in the grid is the deliberate one: the skills
files in the ohs-skills cells.

## Scaffold templates

Three bare repos, cloned per run:

- `templates/cold/` = current `anc-build-a-cold` baseline (`ce135fd`)
- `templates/ohs/` = current `anc-build-b-foundations` baseline (`e414d2f`)
- `templates/ohs-skills/` = ohs baseline + `.claude/skills/{kotlin-fhir,kotlin-fhir-engine,kotlin-fhir-data-capture}/` copied from `ohs-agent-experiment/skills/`, committed as its own baseline

## Per-run sequence

Implemented in `harness/runner.sh`; the nine-step anatomy (preflight
assertions, scaffold clone, server and device resets, capped headless
agent run, environment-fault gate, smoke check, four-artifact export,
teardown) is documented in `../RUNNING.md` section 2.

## What stays manual

- The 2-minute verified-working walk per run (batched; automating UI walks
  over agent-invented UIs isn't worth it at N=27).
- Judgment calls in `run.json.notes` (what the run's interesting moments
  were) — skim the transcript tail, one sentence.

## Failure policy

A run that errors out (harness fault: docker down, emulator dead) is
discarded and re-run — harness faults are not data. A run where the *agent*
fails (doesn't produce a working app within caps) is data: keep it, mark
`verified_working: false`, count its cost. The distinction is recorded in
`run.json.notes`.
