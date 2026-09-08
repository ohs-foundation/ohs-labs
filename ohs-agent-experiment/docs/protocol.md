# Experiment protocol

Two parts. Part A is the original two-build experiment (run 2026-08-23
and 24, reported in `../results/experiment-1.md`). Part B extends it
into the model by condition evaluation grid (ongoing, reported in
`../results/grid.md`). Part A's spec, prompts, and operator rules are
the shared foundation Part B builds on.

The quoted blocks below are the exact texts pasted into agent sessions.
They are data, not prose, and must never be reworded.

---

## Part A. The original two-build experiment

One spec, two agent builds, same rules.

### A1. Ground rules (both builds)

1. Same agent product and same model for both runs, stated in the
   writeup.
2. Fresh session, empty Android project. Only build B starts with the
   extra dependencies listed in its addendum.
3. The spec is pasted verbatim as the opening prompt, followed by the
   build's addendum.
4. Turn budget of 40 user turns per build. Stop there regardless of
   state.
5. The operator behaves like a product owner, not a FHIR expert.
   Answer clarifying questions about what the app should do. Never
   volunteer modeling advice, field names, API names, or standards
   knowledge. Paste build errors, crashes, and server error responses
   back verbatim.
6. If a defect in the prep (seed data, Questionnaire, server config)
   blocks the agent, fix the prep, note it in the transcript, and do
   not count those turns against either build.
7. Save the full transcript of each session. The transcripts are the
   primary artifact.

### A2. The spec (pasted verbatim in both builds)

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

### A3. Build A addendum (cold)

Appended to the opening prompt.

> Use whatever architecture, libraries, data model, and storage you think are
> best. The three existing patients above should be present in the app as
> starting data.

Nothing else. No FHIR server, no FHIR libraries, no hints. If the
agent chooses FHIR on its own, let it and note it in the writeup.

### A4. Build B addendum (OHS)

The project starts with kotlin-fhir (R4 model classes), FHIR Engine,
and Data Capture already declared. Appended to the opening prompt.

> A FHIR R4 server (HAPI) is running at `http://10.0.2.2:8080/fhir` (Android
> emulator's address for the host machine; no auth). It already contains the
> three patients as `Patient` resources with linked `Encounter` and
> `Observation` resources (due date, weight, blood pressure, hemoglobin), and
> a `Questionnaire` with id `anc-contact` for the ANC visit form. The project
> has kotlin-fhir R4 types, FHIR Engine, and the Data Capture library on the
> classpath. Use the server as the source of truth and the Questionnaire for
> the visit form.

When the server rejects a write, paste the `OperationOutcome` body back
to the agent verbatim.

### A5. What to measure

From the transcripts and the final code.

| Metric | How counted |
|---|---|
| Corrective turns | user turns whose only purpose is fixing something the agent got wrong (compile error, crash, wrong behavior, rejected write) |
| Hallucinated APIs | distinct references to methods, classes, or endpoints that do not exist |
| Schema drift | invented field names, types, or structures that diverge from the spec's data or (build B) from FHIR, and renames of the same concept across files |
| Self-corrections from validation | build B only. Times a server `OperationOutcome` led the agent to a correct fix without user help |
| Round-trip success | does a saved visit reappear correctly after app restart |
| Size | lines of hand-written code excluding generated boilerplate, and file count |
| Wall clock and turns | total turns and rough time to first working build |

### A6. Non-goals

No MCP server, no App Shell artifact, no offline story beyond what FHIR
Engine does by default, no skills package, no fhir-gateway, no auth.

### A7. Caveat for the writeup

This is an n-of-1 qualitative comparison, the same as the Health
Samurai article. Report it as suggestive evidence, not proof. Report
the prep cost (server, seed, Questionnaire, roughly 3 to 4 days) as the
cost side of the trade. The rails are not free, they are reusable.

---

## Part B. The evaluation grid and demonstrations

Extends Part A. Two halves with different jobs.

**Measured** covers things that vary run to run because they are agent
behavior. Build cost, time, and whether cheaper models can do the job.
These get repetitions, because run-to-run luck is a possible
explanation that only repetition rules out.

**Demonstrated** covers things that are properties of the architecture
and identical on every run. Form updates, getting data out, bad
records. These are not metrics. They are why the same agent effort
produces more value on the OHS build. Each runs once, to put a real
number and a screen recording on it, and to verify the OHS side
actually delivers before it goes on camera. The footage feeds the demo
(`demo.md`).

Shared rules carry over from Part A. Fresh agent session per run,
prompts pasted verbatim, operator answers product questions only,
errors pasted verbatim. Every run gets a folder under `runs/` (see
`runs/README.md`) holding the four artifacts, plus one row in
`results.csv`.

### B1. Measured. Build cost and time

The original experiment repeated. Same spec prompt, fresh scaffold,
freshly reseeded server, capped headless run.

The first pair (2026-08-23 and 24, claude-fable-5) came out

| | Cold | OHS |
|---|---|---|
| Human effort | 1 prompt, 0 interventions | 1 prompt, 0 interventions |
| Wall clock | about 29 min | about 33 min |
| Compute cost at API rates | about $13 | about $60 |
| Verified working | yes | yes |

The open question repetition answers is whether the cost gap is stable
and whether its composition holds. In the first pair only about $8 of
the gap was code writing. The rest was the agent reverse-engineering
the undocumented SDK, which is the per-build price of having no skills
package.

Per-run metrics are the Part A metrics plus tokens converted to dollars
at that model's rates.

### B2. Measured. Model matrix

Hypothesis. The OHS libraries substitute for model capability. A
cheaper model succeeds with the rails, because types constrain it and
the server corrects it, but struggles cold where nothing catches its
mistakes.

The grid is section 1 of `harness.md`. Conditions cold, ohs, and
ohs-skills against Haiku, Sonnet, Opus, and Fable. Sweep 1 (one run per
cell) is complete, see `../results/grid.md`.

The headline metric is the cheapest model that reliably ships the app,
per condition, and cost per successful build with failed runs charged
to their cell. If rails let Haiku do what cold requires Fable for, that
is up to 10x off the model bill, attributable to the toolkit.

Success or failure per cell is noisy at one run. The claim shape is
"4 of 5 with rails versus 1 of 5 cold", which needs five replicates
per cell.

Fairness. Within any compared set of cells, same agent harness, same
prompts, same settings. Only the model varies, and for cross-agent rows
the explicitly recorded agent. Note model, agent, and settings per run.

**Cross-agent extension.** The same grid can run on a different agent
stack (implemented for Gemini CLI, agent always explicit per run, raw
Gemini model names, rates in `harness/extract-gemini.py`). Report those
rows as a different agent plus model stack, not a pure model
comparison. Switching agent changes the model and the harness driving
it at once, and some metrics map only approximately. There are no
cache-token economics for Gemini, and corrective turns are zero for
all headless runs by construction.

### B3. Demonstrated. Updating the form

The scenario is that the ministry changed the ANC form. Prompt,
verbatim, both builds.

> The ministry of health has updated the standard ANC visit form: it now
> includes a "Fetal heart rate (bpm)" numeric field, recorded at every
> visit. Update the app so nurses can record it and see it in the visit
> history.

Expected shape. OHS is a server-side Questionnaire edit with no app
release. Scratch is schema, form, and detail-screen code changes plus a
rebuild and a redeploy to every phone. Record wall clock on each side
and whether an app release was required.

An unverified claim gets tested here, namely that the OHS app picks up
the edited Questionnaire without a release. That depends on the sync
and caching behavior of FHIR Engine. If it does not hold, that is a
toolkit finding, better found here than in the demo.

### B4. Demonstrated. Getting the data out

The scenario is that the district office needs a report. Prompt,
verbatim, both builds.

> The district health office needs a weekly summary: for the last 7 days,
> each patient who reported any danger sign, with the sign(s), the visit
> date, and their blood pressure that visit. Produce it as a CSV the office
> can open — generated outside the app (they don't have the phone).

Expected shape. On OHS the data is already synced to the server in a
standard format, so the report is one query. On scratch there is no
server. The data only exists on the device, so it takes getting the
file off the phone plus a translator for the app's homemade format.
Even adding a server would not close the gap. It would speak the same
private format, validate nothing, and need hand-built sync. Record wall
clock and lines of integration code.

A fair objection, answered. The scratch build was never asked for an
export, and the agent would happily build an export, a server,
validation, and sync if asked. But each one is then custom software we
own and maintain alone, in a format only this app speaks, and every
future consumer of the data needs another custom integration. Follow
that to its end and you are hand-building a private, worse FHIR. The
demonstration is not that scratch cannot. It is that on OHS it is
already there, standard, and maintained by someone else.

### B5. Demonstrated. Bad records

No agent involved. The operator writes one bad visit record through
each build's storage path, with an invalid status code (`"finaled"`)
and an impossible date (`"2026-13-45"`).

Verified 2026-08-25. HAPI rejects it instantly with one precise error
per problem. The scratch build's database has no rules that could
reject it. The remaining step is to insert the bad row into the scratch
app, re-run the B4 report, and show it poisoning the district numbers
on camera.

A known limit, also verified. Clinically absurd values pass. A systolic
blood pressure of minus 40 in a structurally valid record was accepted,
because base FHIR validation checks structure and codes, not clinical
ranges. Ranges live in profiles, the IG layer, out of scope here.
Report it honestly. It is the concrete motivation for the profile and
IG work. An optional extension is one small ANC profile with min and
max on blood pressure, showing the minus 40 caught too.

### B6. Headline outputs

From the measured half, after repetitions

| | Cold | OHS |
|---|---|---|
| Cost and time to working app, mean and spread | ... | ... |
| Cheapest model that reliably ships it | ... | ... |

From the demonstrated half, once and on camera. Same agent effort,
more valuable output. Form updates without releases, data already
standard on a server, bad records stopped at the door.

### Campaign generations

The prompt and harness have changed in ways that make runs from different
periods non-comparable. Tag each run's generation (stamped in
`run.json.notes`) and never pool across generations.

- **gen-1** (sweep 1, 2026-08): original prompts; fixed-8s smoke check.
- **gen-2** (2026-09): the prompt now instructs the agent to build and run
  the app and fix errors before finishing (identical text in both the cold
  and OHS prompts, so it does not bias the comparison), and verification is
  the deeper `verify.sh` (waits for sync, crash detection, local-DB patient
  count). Expect a higher working rate; that is the intended effect of the
  self-verify instruction, not a skills effect - keep gen-2 skills-on vs
  skills-off comparisons within gen-2.

### B7. Status

1. Phase 1 is done (2026-08-26). Sweep 1 covered every cell once, with
   results and takeaways in `../results/grid.md`. The demonstrations
   (B3 to B5, screen-recorded, demo cut per `demo.md`) are still
   pending.
2. Phase 2 runs the replicates to at least three per cell, five for
   the deciding cells, via the per-agent campaign manifests.
