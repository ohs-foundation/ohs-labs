# Experiment Protocol

Two parts. **Part A** is the original two-build experiment (2026-08-23/24,
reported in `../results/experiment-1.md`). **Part B** extends it into the
model-by-condition evaluation grid (ongoing, reported in
`../results/grid.md`). Part A's spec, prompts, and operator rules are the
shared foundation Part B builds on.

## Part A — the original two-build experiment

One spec, two agent builds, same rules. This document is the fixed part of the
experiment: everything in it applies identically to both runs unless a section
is explicitly marked "Build A only" / "Build B only".

## Ground rules (both builds)

- Same agent product and same model for both runs, stated in the writeup.
- Fresh session, empty Android project (only build B starts with the extra
  dependencies listed in its addendum).
- The spec below is pasted verbatim as the opening prompt, followed by the
  build's addendum.
- Turn budget: 40 user turns per build. Stop there regardless of state.
- The operator (you) behaves like a product owner, not a FHIR expert:
  - Answer clarifying questions about *what the app should do*.
  - Never volunteer modeling advice, field names, API names, or standards
    knowledge in either build.
  - Paste build errors, runtime crashes, and server error responses back
    verbatim when the agent asks or when a run fails.
- If a defect in the prep (seed data, Questionnaire, server config) blocks the
  agent, fix the prep, note it in the transcript, and don't count those turns
  against either build.
- Save the full transcript of each session. The transcripts are the primary
  artifact of the experiment.

## The spec (paste verbatim in both builds)

> Build an Android app for nurses at a small clinic to track antenatal care
> (ANC) visits.
>
> 1. **Register screen:** a list of currently pregnant patients showing name,
>    age, estimated due date, and current weeks of pregnancy, sorted by due
>    date (soonest first).
> 2. Tapping a patient opens a **patient detail screen** showing her past ANC
>    visits: date, weight, blood pressure, and hemoglobin if recorded.
> 3. From the detail screen the nurse can **record a new ANC visit** by
>    filling a form with: visit date, gestational age in weeks, weight (kg),
>    systolic and diastolic blood pressure (mmHg), any danger signs (none /
>    vaginal bleeding / severe headache / blurred vision / fever, multiple
>    allowed), and free-text notes.
> 4. Saving the form persists the visit; it appears in the patient's visit
>    list and survives app restart.
>
> The clinic already has these three patients on file, each with one prior
> visit:
>
> | Name | Date of birth | Est. due date | Last visit | Weight | BP | Hb |
> |---|---|---|---|---|---|---|
> | Emily Carter | 1996-04-12 | 2026-12-05 | 2026-08-10 | 68.5 kg | 118/76 | 11.8 g/dL |
> | Sarah Mitchell | 1990-11-02 | 2027-01-20 | 2026-08-12 | 61.2 kg | 110/70 | 12.4 g/dL |
> | Grace Thompson | 2001-07-30 | 2026-10-15 | 2026-08-05 | 72.0 kg | 128/84 | 10.2 g/dL |

## Build A addendum ("cold")

Append to the opening prompt:

> Use whatever architecture, libraries, data model, and storage you think are
> best. The three existing patients above should be present in the app as
> starting data.

Nothing else. No FHIR server, no FHIR libraries, no hints. If the agent
chooses FHIR on its own, let it — note it in the writeup.

## Build B addendum ("FHIR Foundations")

The project starts with these dependencies already declared: `kotlin-fhir`
(R4 model classes), Android FHIR Engine, Android FHIR Data Capture (SDC).
Append to the opening prompt:

> A FHIR R4 server (HAPI) is running at `http://10.0.2.2:8080/fhir` (Android
> emulator's address for the host machine; no auth). It already contains the
> three patients as `Patient` resources with linked `Encounter` and
> `Observation` resources (due date, weight, blood pressure, hemoglobin), and
> a `Questionnaire` with id `anc-contact` for the ANC visit form. The project
> has kotlin-fhir R4 types, FHIR Engine, and the Data Capture library on the
> classpath. Use the server as the source of truth and the Questionnaire for
> the visit form.

When the server rejects a write, paste the `OperationOutcome` body back to
the agent verbatim.

## What to measure (from the transcripts and final code)

| Metric | How counted |
|---|---|
| Corrective turns | User turns whose only purpose is fixing something the agent got wrong (compile error, crash, wrong behavior, rejected write) |
| Hallucinated APIs | Distinct references to methods/classes/endpoints that don't exist |
| Schema drift | Invented field names, types, or structures that diverge from the spec's data or (build B) from FHIR; renames of the same concept across files |
| Self-corrections from validation | (Build B) times a server `OperationOutcome` led the agent to a correct fix without user help |
| Round-trip success | Does a saved visit reappear correctly after app restart? |
| Size | Lines of hand-written code (exclude generated/boilerplate), file count |
| Wall-clock and turns | Total turns and rough time to first working build |

## Non-goals (per the PoC doc)

No MCP server, no App Shell artifact, no offline story beyond what FHIR
Engine does by default, no skills package, no fhir-gateway, no auth.

## Caveat for the writeup

This is an n-of-1 qualitative comparison, same as the Health Samurai article.
Report it as suggestive evidence, not proof, and report the prep cost
(server + seed + Questionnaire, roughly 3–4 days) as the cost side of the
trade — the rails aren't free, they're reusable.


---

## Part B — the evaluation grid and demonstrations

Extends Part A. Two parts with different jobs:

- **Part 1 — Measured.** Things that vary run to run (agent behavior):
  build cost/time, and whether cheaper models can do the job. These get
  repetitions, because run-to-run luck is a possible explanation that
  repetition rules out.
- **Part 2 — Demonstrated.** Things that are properties of the
  architecture, identical on every run: form updates, getting data out,
  bad records. These are not metrics — they are *why the same agent
  effort produces more value on the OHS build*. Each runs **once**, to
  put a concrete number and screen recording on it (and to verify the
  OHS side actually delivers what we claim), then feeds the demo video.

Rules carry over from Part A: fresh agent session per run, prompts
pasted verbatim, operator answers product questions only, errors pasted
verbatim. Every run gets a folder under `runs/` named
`s<scenario>-<condition>-<model>-<replicate>` (see `runs/README.md`) holding
transcript, `run.json`, and `code.diff`, plus one row appended to
`results.csv`. Screen-record every session — recordings feed the demo
(`demo.md`).

---

### Part 1 — Measured (repeated runs)

### 1a. Build cost and time

The original experiment, repeated: same spec prompt, fresh scaffold and
freshly reseeded HAPI per run, auto-accept, turn/token cap.

First run (2026-08-23/24, claude-fable-5):

| | Scratch (cold) | OHS (Foundations) |
|---|---|---|
| Human effort | 1 prompt, 0 interventions | 1 prompt, 0 interventions |
| Wall clock | ~29 min | ~33 min |
| Compute cost (API rates) | ~$13 | ~$60 |
| Verified working | yes | yes |

Open question repetition answers: is the ~$47 gap stable, and does its
composition hold (first run: only ~$8 of it was code-writing; the rest
was cache reads from the agent reverse-engineering the undocumented SDK —
i.e. the per-build price of having no skills package)?

Per-run metrics: verified-working (compiles, installs, walks the three
screens, visit survives restart), corrective turns, wall clock, tokens →
dollars at that model's rates, self-corrections, hallucinated APIs.

### 1b. Model matrix

Hypothesis: the OHS libraries substitute for model capability — a cheaper
model succeeds with the rails (types constrain it, the server corrects it)
but struggles cold (nothing catches its mistakes).

Grid: {cold, foundations} × {haiku, sonnet, fable}. Rates (input/output
per MTok; cache read = 0.1× input): Haiku 4.5 $1/$5 · Sonnet 5 $2/$10 ·
Fable 5 $10/$50. The fable cells are done (first run above).

Headline metric: **cheapest model that reliably ships the app, per
condition** — and cost per *successful* build (failed runs charged to the
condition). If rails let Haiku do what cold requires Fable for, that's up
to ~10× off the model bill, attributable to the toolkit.

Success/failure per cell is noisy at n=1 — the claim shape is
"4/5 with rails vs 1/5 cold", which needs n≥5 per cell (phase 2).

Fairness: same Claude Code harness, same prompts, same effort settings,
model switched via `claude --model` only; note model + settings per run.

---

### Part 2 — Demonstrated (one run each)

Not metrics. The outcome cannot vary between runs — it is decided by the
architecture. One run each serves three purposes: put a real number on the
contrast, **verify the OHS side actually delivers the claim** before we
put it on camera, and produce the demo footage.

### 2a. Updating the form ("the ministry changed the ANC form")

Prompt (verbatim, both builds):

> The ministry of health has updated the standard ANC visit form: it now
> includes a "Fetal heart rate (bpm)" numeric field, recorded at every
> visit. Update the app so nurses can record it and see it in the visit
> history.

Expected: OHS = server-side Questionnaire edit, no app release; scratch =
schema + form + detail-screen code changes, rebuild, redeploy to every
phone. Record: wall clock each side, and whether an app release was
required.

⚠ Unverified claim to test here: that the OHS app picks up the edited
Questionnaire without a release (sync/caching behavior of FHIR Engine).
If it doesn't, that's a toolkit finding — better found here than in the
demo.

### 2b. Getting the data out ("the district office needs a report")

Prompt (verbatim, both builds):

> The district health office needs a weekly summary: for the last 7 days,
> each patient who reported any danger sign, with the sign(s), the visit
> date, and their blood pressure that visit. Produce it as a CSV the office
> can open — generated outside the app (they don't have the phone).

Expected: OHS = the data is already synced to HAPI in a standard format —
one query. Scratch = no server; the data only exists on the device, so
it's get-the-file-off-the-phone plus a translator for the app's homemade
format — and even adding a server wouldn't close the gap: it would speak
that same private format, validate nothing, and need hand-built
device-to-server sync. Record: wall clock, lines of integration code.

**"Isn't this unfair — the scratch build was never asked for an export?"**
Correct, and it could be asked — the agent will happily build an export, a
server, validation, sync. But each is then custom software we own and
maintain alone, in a format only this app speaks, and every future
consumer of the data needs another custom integration against it. Follow
that to its end and you are hand-building a private, worse FHIR. The
demonstration isn't "scratch can't" — it's "on OHS it's already there,
standard, and maintained by someone else."

### 2c. Bad records ("is the data safe from silent corruption?")

No agent — the operator writes one bad visit record through each build's
storage path: invalid status code (`"finaled"`) + impossible date
(`"2026-13-45"`).

**Verified 2026-08-25:** HAPI rejects it instantly, one precise error per
problem. SQLite accepts the equivalent row silently. Remaining step:
insert the bad row into build A, re-run 2b's report, show it poisoning
the district numbers — on camera.

**Known limit (also verified):** clinically absurd values pass — a
systolic BP of −40 in a structurally valid observation was accepted.
Base FHIR validation checks structure and codes, not clinical ranges;
ranges live in profiles (the IG layer), out of scope for this PoC.
Report honestly; it is the concrete motivation for the profile/IG work.
Optional extension: one small ANC profile with min/max on BP, showing
the −40 caught too — "app is the IG" in a single StructureDefinition.

---

### The headline outputs

**From Part 1** (after repetitions):

| | Scratch | OHS |
|---|---|---|
| Cost / time to working app (mean ± spread) | … | … |
| Cheapest model that reliably ships it | … | … |

**From Part 2** (once, on camera): same agent effort, more valuable
output — form updates without releases, data already standard on a
server, bad records stopped at the door.

### Phases

- **Phase 1 (this week):** Part 2 runs (one each) + the four new model
  cells (haiku/sonnet × cold/foundations) once each. Everything
  screen-recorded; demo cut from the footage per `demo.md`.
- **Phase 2:** headless runner repeats Part 1 to n≥5 per cell (fresh
  scaffold + HAPI reset per run; automated scoring: functional walk,
  interop checks, transcript metrics). Later adds a third condition —
  Foundations + skills package — whose predicted effect is the OHS build
  cost dropping toward the scratch build's.
