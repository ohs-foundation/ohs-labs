# Harness design

Why the run automation is shaped the way it is. The step-by-step of what
a run does lives in `../RUNNING.md`. The protocol it implements is
`protocol.md` Part B.

## 1. The grid

Skills only make sense on the OHS build, so the grid has 12 cells.

| | fable | opus | sonnet | haiku |
|---|---|---|---|---|
| cold (scratch) | x | x | x | x |
| ohs (OHS libraries) | x | x | x | x |
| ohs-skills (libraries plus agent docs) | x | x | x | x |

Three replicates per cell, five for the cells that decide claims (the
haiku rows and the fable ohs versus ohs-skills pair). Run order matters.
One full sweep of every cell first for early signal on every claim, then
the remaining replicates interleaved rather than cell by cell, which
spreads time-of-day effects and flakiness evenly.

## 2. Multi-agent design

Claude and Gemini are implemented. Others follow the same pattern (see
section 6). The rule throughout is that the agent is an attribute of a
run, never a folder hierarchy, and never a default.

1. One `runs/` tree, one `results.csv`, one grid. A run's model segment
   already implies its agent (`opus` is Claude, `gemini-3.7-flash` is
   Gemini, no overlap) and `run.json` records the harness explicitly.
2. The agent is the explicit first argument of every run
   (`./runner.sh claude opus ohs 02`). There is no default agent, no
   default manifest, and no file named as if one agent were the normal
   case. Each agent has its own extractor (`extract-claude.py`,
   `extract-gemini.py`) and its own campaign manifest
   (`manifest-claude.txt`, `manifest-gemini.txt`).
3. Shared templates carry no agent instruction files at all.
   Agent-specific instruction files live only inside that agent's own
   skills template. One template never carries two agents' files,
   because each agent could discover the other's.

## 3. Scaffold templates

Four bare repos, cloned per run, built from the committed sources in
`harness/template-src/` by `harness/setup-templates.sh` (idempotent,
run once after cloning the repo).

| Template | Contents |
|---|---|
| `cold` | empty scaffold, agent picks its own stack |
| `ohs` | scaffold with the three OHS libraries declared |
| `ohs-skills-claude` | ohs plus `skills/` as `.claude/skills/` |
| `ohs-skills-gemini` | ohs plus the same skills as one `GEMINI.md` |

The runner picks the template from condition plus agent. The
`ohs-skills` condition selects `ohs-skills-claude` or
`ohs-skills-gemini` by agent.

## 4. Cleanliness contract

Every run must start with zero trace of any previous run. Six kinds of
state, each with its cleaner and its check.

| State | Risk | Cleaned by | Checked by |
|---|---|---|---|
| Agent session and memory | resumed session, project memory, history | fresh directory per run, cloned from the template. A new path means a new project for either agent, with empty history and memory | runner asserts no prior agent state exists for the work path |
| Global instruction files | `~/.claude/CLAUDE.md` and `~/.gemini/GEMINI.md` are injected into every session of their agent | audit before a campaign that both are empty or absent | manual audit, plus the runner refuses a gemini run while a non-empty `~/.gemini/GEMINI.md` exists |
| Server | previous run's uploaded resources and sync watermarks | container destroyed, recreated, and reseeded before every run, cold runs included, so the environment is constant | seed script verifies resource counts |
| Device | installed APKs, on-device databases, queued sync work | uninstall sweep of every `com.example.*` package before and after each run | runner asserts the device is clean before starting |
| Build caches | the first run would pay dependency downloads that later runs skip | warm the shared Gradle cache once per template before any measured run, so cache state is a constant for everyone | throwaway warm builds done during setup |
| Filesystem neighbors | with permissions bypassed an agent could list its way into a previous run's folder and find a finished solution | each run's work folder is archived away at teardown | runner asserts the work area holds only the current run |

Two agent-specific channels deserve their own mention.

**Gemini global memory.** Gemini's save_memory tool writes to the
global `~/.gemini/GEMINI.md`, which every later session auto loads. A
run could leave notes for the next run. The runner refuses to start a
gemini run while that file exists non-empty, and at teardown it
quarantines anything an agent wrote into the run's folder as
`global-memory-left-by-agent.md`. Kept as evidence, never fed forward.

**Instruction files above the work dirs.** Both agents auto load their
instruction files from ancestor directories too. So no `CLAUDE.md` or
`GEMINI.md` may exist anywhere in the repo above `harness/work/`. They
may exist only inside an agent's own skills template.

The models themselves carry nothing between sessions. There is no
server-side memory of past conversations for either agent. With the
channels above closed, the only knowledge injection anywhere in the
grid is the deliberate one, the skills files in the ohs-skills cells.

## 5. Failure policy

A run that fails for environment reasons (docker down, emulator dead,
network out, API auth, usage or quota limit) is a harness fault. It is
discarded, never counted, and the campaign halts so faults cannot pile
up junk. A run where the agent itself fails to produce a working app
within the caps is data. Keep it, mark `verified_working` false, and
count its cost against the cell.

Two things stay manual on purpose.

1. The verified-working walk per run, because agents invent different
   UIs every run and automated walks over unknown UIs are not worth it
   at this scale. Broken apps have passed every automated check twice.
2. A one-line judgment note in `run.json` about the run's interesting
   moments, written after skimming the transcript tail.

## 6. Adding a new agent

The layout is designed so a new agent (say Qwen) is additive. Nothing
about existing agents, runs, or results changes. Two halves.

The mechanical half, a few hours of work.

1. `runner.sh` gains a branch in the agent case. Binary resolution,
   model name rule, the agent's API endpoint for the connectivity
   preflight, the headless invocation (prompt in, tools auto approved,
   transcript captured), and where the transcript comes from.
2. `extract-<agent>.py` parses that transcript into the same `run.json`
   fields and the same `results.csv` row shape, with a rates table for
   cost. Copy the closest existing extractor and adjust.
3. `setup-templates.sh` gains an `ohs-skills-<agent>` template that
   packages the same three skills as whatever file the agent auto
   loads. The skills themselves are plain markdown and never change.
4. A `manifest-<agent>.txt` campaign file.
5. Docs. The supported models table and prerequisites in `RUNNING.md`,
   and the template list here.

The investigation half, where the real care goes.

6. The isolation audit cannot be copied, only re-earned per agent.
   Discover where the agent persists sessions, whether it has a memory
   feature and where it writes (gemini's global memory leak was found
   only by looking), which global instruction files it auto loads (add
   them to the rules in section 4), and what its quota and error
   messages look like for the fault gate.
7. One probe run with the transcript eyeballed before trusting any
   metrics, the same ritual every agent went through.

What never changes. The `runs/` structure, the `results.csv` shape,
the prompts, the conditions, the grid logic, and every other agent's
code paths. A new agent's runs are just new rows in the same table.
