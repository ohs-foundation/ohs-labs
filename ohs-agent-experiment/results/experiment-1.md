# App Is the IG — ANC PoC: Results

*Experiment run 2026-08-23/24 per `../docs/protocol.md` Part A. One operator, same agent
(Claude Code, `claude-fable-5`, auto-accept mode) for both builds, identical
spec pasted verbatim, fresh sessions, empty Android scaffolds differing only
in build B's three declared dependencies (`dev.ohs.fhir:fhir-model`,
`fhir-engine`, `fhir-data-capture`).*

## Headline

Both builds succeeded, end to end, with **zero corrective turns** — the
operator pasted the spec once and never had to intervene; each agent built,
ran, and verified its own app on the emulator in ~30 minutes. The
Health Samurai claim held on our stack, but in a sharper form than "the cold
agent drifts and fails": **a strong agent succeeds either way — what the FHIR
rails change is what the success is made of.** The cold build produced a
working island: an invented private schema no other system can read. The
Foundations build produced standard FHIR resources on a server, a form
rendered from a portable Questionnaire artifact, and — the money moment — a
server validation error that led the agent to find and work around a real bug
in our own SDK, with no human help.

## The numbers

| Metric | Build A (cold) | Build B (Foundations) |
|---|---|---|
| User turns / corrective turns | 1 / 0 | 1 / 0 |
| Wall clock | ~29 min | ~33 min |
| Tool calls | 45 | 122 |
| Compile/build failures (self-fixed) | 2 (dep versions) | 1 (variable shadowing) |
| Runtime crashes (self-fixed) | 0 | 1 (`DataCapture` init) |
| Server validation incidents | n/a | 1 (HTTP 422 → self-corrected) |
| Hallucinated APIs in final code | 0 | 0 |
| Kotlin lines added | 657 | 946 |
| — of which the visit form | 227 | 91 |
| — of which data/sync plumbing | 171 | 505 |
| Round-trip (restart persistence) | pass | pass, incl. server round-trip |
| Where the data lives | app-private SQLite | HAPI: `Encounter` + 5 `Observation`s (LOINC/UCUM) + linked `QuestionnaireResponse` |

## Build A: clean run, competent app, textbook schema invention

The cold agent chose Compose + Navigation + Room, built the app in one
autonomous pass, and verified everything itself. Its two build failures were
version guesses (a lifecycle artifact needing a newer AGP; material icons no
longer bundled in recent Compose BOMs), both fixed from compile errors.

The evidence isn't failure — it's invention. Every data decision is a
private, one-off convention: its own `Patient`/`Visit` schema, dates stored
as ISO strings so SQL sorting works, danger signs stored as a
**comma-joined string in one column**, seed patients hardcoded as SQL in the
database-creation callback. Locally reasonable, collectively disposable: no
other system can read this data, nothing validates any write, and a second
app — or the same agent on a different day — would reinvent all of it
differently. The 227-line hand-built form is the largest file in the app.

## Build B: the rails in action

Three observations, in increasing order of importance.

**1. With no docs, the agent grounded itself in the artifacts.** The first
~10 minutes were spent unpacking the cached jars, running `javap`, and
reading the bundled sources to learn the exact API surface — sync worker,
search DSL, builder patterns, the Compose `Questionnaire(...)` entry point —
before writing a line of app code. It worked (zero hallucinated APIs
survived), but it is exactly the cost a **skills package** exists to remove.
The transcript is a to-do list for what those skills should say.

**2. The Questionnaire earned its keep.** The visit form is 91 lines versus
build A's 227, because the Data Capture library renders the server's
`anc-contact` Questionnaire directly — date picker, numeric vitals,
multi-select danger signs, all from the artifact. Changing the form is now a
server-side edit, no app release. The flip side: mapping the submitted
`QuestionnaireResponse` to `Encounter`/`Observation` resources is 400+ lines
of hand-written repository code — the single biggest file in either build —
because we ship no SDC extraction support yet. That's the clearest
next-investment signal in the data.

**3. The validation loop did what the article promised — against our own
SDK.** The first sync upload was rejected by HAPI with a 422
`OperationOutcome` (`BUNDLE_ENTRY_URL_ABSOLUTE`: the engine's
transaction-bundle generator emits a `fullUrl` form HAPI's validator
refuses — an apparent upstream bug in `fhir-engine 2.0.0-alpha02`'s
`BundleEntryComponentGenerator`). The agent found the error in logcat,
read the engine's bundle-generation code, concluded the bug was in the
library, and switched the upload strategy to individual PUT requests with
client-assigned IDs — sidestepping the broken path. Data landed on the
server; no human touched the exchange. A generic backend would have
accepted the malformed write silently or failed opaquely; the typed
rejection is what made the self-correction possible.

## What the experiment cost, and what it found for free

Prep (HAPI in Docker, a seeded ANC bundle, one Questionnaire, the protocol)
took roughly 3–4 days and is reusable for everything that follows. The two
agent runs took about half an hour each. Along the way the experiment
surfaced three concrete pieces of SDK feedback at zero extra cost: the
transaction-bundle `fullUrl` bug above; the `dev.ohs.fhir` artifacts being
compiled for JVM 21 (forcing consumers to bump `jvmTarget`); and
`DataCapture` requiring explicit initialization (first use crashes
otherwise — worth an init-check error message or lazy init).

## Caveats

n=1, qualitative, same operator for both runs, and the operator never
needed to exercise the corrective-turn protocol — so this says nothing yet
about how the two stacks compare when an agent *does* go wrong. Build B also
benefits from prep the cold build didn't use (server, seed, Questionnaire);
we report that as the cost side of the trade, not a freebie. And one run of
each tells us nothing about variance between runs.

## Verdict and next step

The claim reproduced: FHIR Foundations turned the same agent effort into
standard, interoperable, server-validated output, and the validation loop
demonstrably corrected a real integration failure without human help. The
delta also priced the gaps precisely — the agent's 10 minutes of API
archaeology is the skills package's job, and the 400-line mapping layer is
SDC extraction's job.

Recommended next step from the PoC doc's menu: **the skills package first**
(cheapest, directly measured by this experiment, and it compounds — every
future agent run benefits), with the MCP server as the follow-on once
skills exist for it to serve. The App Shell remains the bigger bet.

---

*Artifacts: `runs/s1-cold-fable-01/` and `runs/s1-ohs-fable-01/` (each:
transcript.jsonl, transcript.md, run.json, code.diff), plus git repos
`anc-build-a-cold` (result on `ce135fd` baseline) and
`anc-build-b-foundations` (result on `e414d2f` baseline). Scorecard index:
`results.csv`.*

*TODO before sharing: embed the three screenshots per build (register,
detail, form).*
