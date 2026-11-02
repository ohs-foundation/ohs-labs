# Experiment design

How the experiment works and why. The rules every run follows, and how
the harness enforces them so runs are comparable. The step-by-step of a
run is in `../RUNNING.md`, and the results are in
`blog-interoperability-tax.md`.

## 1. The task

Every agent gets the same app spec. Build an Android app for nurses at a
small clinic to track antenatal care (ANC) visits, with

1. a register of currently pregnant patients, sorted by due date
2. a patient screen with past visits
3. a form to record a new visit (date, gestational age, weight, blood
   pressure, danger signs, notes)
4. visits that survive an app restart

The clinic already has three patients, each with one past visit. The
prompt ends by telling the agent to build and run the app and fix every
error before it finishes.

The exact prompt for each condition is in `../build-a-prompt.md`
(`cold`), `../build-c-prompt.md` (`fhir`) and `../build-b-prompt.md`
(`ohs` and `ohs-skills`). They are pasted verbatim and must never be
reworded.

## 2. The grid

Four conditions (`cold`, `fhir`, `ohs`, `ohs-skills`, described in
`../README.md`) against each model, two runs per cell, on the models
listed in `../README.md`. Skills only make sense on the OHS build, so
`ohs-skills` is the only skills cell.

Run order matters. Do one sweep of every cell first, then interleave
the remaining runs rather than going cell by cell, which spreads
time-of-day effects and flakiness evenly.

## 3. Run rules

1. One prompt, no human input. The agent runs headless with
   permissions auto-approved.
2. A clean slate for every run (section 7).
3. A 60 minute wall-clock cap.
4. Environment failures are discarded and agent failures are kept
   (section 8).
5. The only knowledge given to the agent on purpose is the skills, in
   the `ohs-skills` condition. Every other channel is closed (section 7).

## 4. What is measured

| Measure | How |
|---|---|
| Cost | Tokens from the transcript at the model's API prices |
| Time | Wall clock from the first to the last message |
| Effort | Tool calls, failed builds, and server rejections (`OperationOutcome`) |
| Quality | A person scores the app on 10 checks, one point each, see `../results/app-scores.md` |

Every metric per run is in `../results.csv`, described in
`../runs/README.md`.

The quality walk stays manual on purpose. Agents invent a different UI
every run, so an automated walk over unknown UIs is not worth it at this
scale, and broken apps have passed every automated check before.

## 5. Comparing runs

1. Within a compared set, the agent, prompt and settings are the same.
   Only the model or the condition changes.
2. Runs made with different skills versions are not pooled (see
   `../skills/CHANGELOG.md`).
3. Gemini CLI and Antigravity are different agents. Compare their rows
   as agent plus model, not as the model alone.
4. The skills are not delivered identically. Claude and Antigravity
   load the three skills on demand, and Gemini CLI gets them
   concatenated and always on (section 6).
5. Gemini CLI's output tokens exclude thinking, so its cost is a lower
   bound.

## 6. Agents and templates

Claude Code, Gemini CLI, and Antigravity CLI are implemented. Gemini CLI
and Antigravity CLI both drive Gemini models. They are two harnesses
over one model family, and both stay supported so the effect of the
harness itself can be measured at a fixed model. The rule throughout is
that the agent is an attribute of a run, never a folder hierarchy, and
never a default.

1. One `runs/` tree, one `results.csv`, one grid. A run's model segment
   already implies its agent (see `../runs/README.md`) and `run.json`
   records the harness explicitly.
2. The agent is the explicit first argument of every run
   (`./runner.sh claude claude-opus-5-5-medium ohs 1`). There is no
   default agent and no default manifest. Each agent has its own
   extractor (`extract-claude.py`, `extract-gemini.py`,
   `extract-antigravity.py`) and its own campaign manifest. The two
   Gemini-model extractors share one rates table.
3. Shared templates carry no agent instruction files at all.
   Agent-specific instruction files live only inside that agent's own
   skills template. One template never carries two agents' files,
   because each agent could discover the other's.

Each run clones one of six bare template repos, built from
`../harness/template-src/` by `harness/setup-templates.sh` (idempotent,
run once after cloning the repo). The runner picks the template from
condition plus agent.

| Template | Contents |
|---|---|
| `cold` | empty scaffold, agent picks its own stack |
| `fhir` | empty scaffold with internet permission, used with the FHIR server and `build-c-prompt.md` |
| `ohs` | scaffold with the three OHS libraries declared |
| `ohs-skills-claude` | ohs plus `skills/` as `.claude/skills/` |
| `ohs-skills-gemini` | ohs plus the same skills as one `GEMINI.md` |
| `ohs-skills-antigravity` | ohs plus `skills/` as `.agents/skills/` (agy's skill layout, loaded on demand like Claude's) |

## 7. Clean slate

Every run must start with zero trace of any previous run. Six kinds of
state, each with its cleaner and its check.

| State | Risk | Cleaned by | Checked by |
|---|---|---|---|
| Agent session and memory | resumed session, project memory, history | fresh directory per run, cloned from the template. A new path means a new project for every agent, with empty history and memory | runner asserts no prior agent state exists for the work path (Claude: no project dir, Antigravity: no entry in `last_conversations.json`) |
| Global instruction files | `~/.claude/CLAUDE.md` and `~/.gemini/GEMINI.md` are injected into every session of their agent, and agy also loads `~/.gemini/config/` | audit before a campaign that both are empty or absent | manual audit (list in `../RUNNING.md` section 1), plus a runner preflight for gemini and antigravity runs |
| Server | previous run's uploaded resources and sync watermarks | container destroyed, recreated, and reseeded before every run, cold runs included, so the environment is constant | seed script fails if the server rejects the seed bundle, and prints resource counts next to the expected ones |
| Device | installed APKs, on-device databases, queued sync work | uninstall sweep of every `com.example.*` package before and after each run | runner asserts the device is clean before starting |
| Build caches | the first run would pay dependency downloads that later runs skip | warm the shared Gradle cache once per template before any measured run, so cache state is a constant for everyone | throwaway warm builds done during setup |
| Filesystem neighbors | with permissions bypassed an agent could list its way into a previous run's folder and find a finished solution | each run's work folder is archived away at teardown | runner asserts the work area holds only the current run |

Three agent-specific channels deserve their own mention.

**Gemini global memory.** Gemini's save_memory tool writes to the
global `~/.gemini/GEMINI.md`, which every later session auto loads. A
run could leave notes for the next run. The runner refuses to start a
gemini run while that file exists non-empty, and at teardown it
quarantines anything an agent wrote into the run's folder as
`global-memory-left-by-agent.md`. Kept as evidence, never fed forward.

**Antigravity knowledge store and scratch folder.** agy keeps a
knowledge store at `~/.gemini/antigravity-cli/knowledge/` that the agent
can write to (it ships a `delete_knowledge` tool). The runner refuses to
start while it holds anything and quarantines whatever a run adds into
`runs/<id>/knowledge-left-by-agent/`. Separately, headless agy works in
a private scratch folder (`~/.gemini/antigravity-cli/scratch/`) unless
the work dir is passed with `--add-dir`. The runner always passes it,
and the probe run checks the app really landed in the work folder.
Headless agy also ends the session when the model yields on a
background command. agy backgrounds any command that outlives its
per-call wait (a Gradle build does) and invites the model to carry on
or "update the user". In the TUI the task's completion wakes the agent,
headless, the session just ends. Two early runs shipped zero lines this
way while the smoke check passed on the untouched template. So while
the last step in agy's conversation log is a still-running background
task, the runner resumes the conversation with a continue prompt that
says nothing about the task, and records the count as `resume_turns`.
That is a harness mechanic applied uniformly to every antigravity run,
not a corrective turn. Conversations themselves are stored globally by
id under `~/.gemini/antigravity-cli/{conversations,brain}/`, keyed to
the cwd only through `cache/last_conversations.json`, so a fresh path is
a fresh conversation.

**Instruction files above the work dirs.** All agents auto load their
instruction files from ancestor directories too (agy: `GEMINI.md`,
`AGENTS.md`, `.agents/rules/*.md`, walking up to the repository root).
So no `CLAUDE.md`, `GEMINI.md`, or `AGENTS.md` may exist anywhere in the
repo above `harness/work/`. They may exist only inside an agent's own
skills template.

The models themselves carry nothing between sessions. There is no
server-side memory of past conversations for any of the agents. With the
channels above closed, the only knowledge injection anywhere in the
grid is the deliberate one, the skills files in the ohs-skills cells.

## 8. Failure policy

A run that fails for environment reasons (docker down, emulator dead,
network out, API auth, zero tool calls, usage or quota limit) is a
harness fault. It is discarded, never counted, and the campaign halts so
faults cannot pile up junk. A run where the agent itself fails to
produce a working app within the caps is data. Keep it, mark
`verified_working` false, and count its cost against the cell.

## 9. Adding a new agent

The layout is designed so a new agent (say Qwen) is additive. Nothing
about existing agents, runs, or results changes. Two halves.

The mechanical half, a few hours of work.

1. `runner.sh` gains a branch in the agent case. Binary resolution,
   model name rule, the agent's API endpoint for the connectivity
   preflight, the headless invocation (prompt in, tools auto approved,
   transcript captured), where the transcript comes from, and the fault
   gate: how to count tool calls and the agent's quota and error
   messages.
2. `extract-<agent>.py` parses that transcript into the same `run.json`
   fields and the same `results.csv` row shape, with a rates table for
   cost. Copy the closest existing extractor and adjust.
3. `setup-templates.sh` gains an `ohs-skills-<agent>` template that
   packages the same three skills as whatever file the agent auto
   loads. The skills themselves are plain markdown and never change.
4. A `manifest-<agent>.txt` campaign file.
5. Docs. The supported models table and prerequisites in `RUNNING.md`,
   and the template list in section 6.

The investigation half, where the real care goes.

6. The isolation audit cannot be copied, only re-earned per agent.
   Discover where the agent persists sessions, whether it has a memory
   feature and where it writes (gemini's global memory leak was found
   only by looking), which global instruction files it auto loads (add
   them to section 7), what its quota and error messages look like for
   the fault gate, and whether it honours the requested model, and
   where the answering model is recorded (gemini-cli silently swapped
   flash names, and agy's stream only echoes the request, the answering
   model is in its conversation db).
7. One probe run with the transcript eyeballed before trusting any
   metrics, the same ritual every agent went through.

What never changes. The `runs/` structure, the `results.csv` shape,
the prompts, the conditions, the grid logic, and every other agent's
code paths. A new agent's runs are just new rows in the same table.

## 10. Known limits

- Two runs per cell. Differences are signals, not proof.
- One task, on one platform (Android).
- The cost of preparing the FHIR server, seed data and Questionnaire is
  not counted.
- FHIR validation on the server checks structure and codes, not clinical
  ranges. A systolic blood pressure of minus 40 in a well-formed record
  is accepted. Ranges belong in profiles, which this experiment does not
  use.
