# OHS agent experiment

Measures what it costs an AI coding agent to build a standards-based
(FHIR) health app compared with a custom one, and whether the OHS
libraries and agent skills change that. The idea comes from a [Health
Samurai
article](https://www.health-samurai.io/articles/fhir-as-a-framework-for-agentic-coding)
which showed with impressions that agents build more coherent apps on a
FHIR stack. This experiment tests the claim on the OHS stack with
measurements.

## Start here

| You want to | Read |
|---|---|
| See the results | [docs/blog-interoperability-tax.md](docs/blog-interoperability-tax.md) |
| See every app's score | [results/app-scores.md](results/app-scores.md) |
| Run one build yourself | [Run one build](#run-one-build), below |
| Run campaigns, walk apps, fix faults | [RUNNING.md](RUNNING.md) |
| Score an app on the 10 checks | [harness/walk/README.md](harness/walk/README.md) |
| Look up a run folder or a `results.csv` column | [runs/README.md](runs/README.md) |
| Understand the run rules and why the harness works this way | [docs/design.md](docs/design.md) |
| Read or change the skills | [skills/README.md](skills/README.md) |

## How we test it

An AI agent gets the same antenatal care (ANC) app spec and builds it
under one of four conditions.

| Condition | Also called | Prompt | What the agent gets |
|---|---|---|---|
| `cold` | No FHIR, build A | `build-a-prompt.md` | An empty project. It picks its own stack and storage. |
| `fhir` | FHIR without OHS, build C | `build-c-prompt.md` | The FHIR server and seed data, no OHS libraries. |
| `ohs` | OHS, build B | `build-b-prompt.md` | The three OHS libraries and the FHIR server. |
| `ohs-skills` | OHS + Skills | `build-b-prompt.md` | The same as `ohs`, plus the [skills](skills/) for the libraries. |

Each condition ran twice on Claude Haiku 5.5, Sonnet 5.5, Opus 5.5 and
Fable 5.1 (Claude Code) and Gemini 3.8 Flash and Gemini 4 Argon
(Antigravity CLI), all at medium effort. Gemini 4 Argon has no `fhir`
runs. The harness gives every run a clean slate. Fresh
session, fresh folder, reset server, wiped device.

We measure two things.

1. **Does the app work.** A person installs every app and scores it on
   10 checks, from listing patients to uploading a visit saved offline
   after the app is closed.
2. **Cost and time per build**, from the agent transcripts at API
   prices.

## Results

With skills, Gemini 3.8 Flash, Gemini 4 Argon, Sonnet, Opus and Fable
each built a fully working FHIR app (10 out of 10) for 50 cents more on
average than the custom app. For those five, the custom apps scored 6
out of 10, and
the OHS apps without skills scored 6 to 8 and cost the most. Haiku never
built a FHIR app that works offline, even with skills. The cost and time
table is in the [blog](docs/blog-interoperability-tax.md), and every
app's score in [results/app-scores.md](results/app-scores.md).

### Runs used in the blog

| Condition | Claude models | Gemini 3.8 Flash | Gemini 4 Argon |
|---|---|---|---|
| `cold` | runs 1, 2 | runs 1, 2 | runs 1, 2 |
| `ohs` | runs 1, 2 | runs 1, 2 | runs 2, 3 |
| `ohs-skills` (skills v2.5) | runs 8, 9 | run 15 | runs 3, 4 |

Run ids are `s1-<condition>-<model>-<run>`, e.g.
`s1-ohs-skills-claude-opus-5-5-medium-8` or
`s1-cold-gemini-3.8-flash-medium-1`. The other runs are earlier skills
versions, the `fhir` baseline, or one extra Gemini run at low effort.

Rerunning the blog's 45 runs (the three conditions above for all six
models plus the `fhir` baseline) costs about $68 at API prices and about
6 hours of agent time, plus about 10 minutes per app to score it.

Charts: `python3 results/plot_charts.py` (needs matplotlib) redraws
`results/cost-by-model.png` and `results/minutes-by-model.png` from
`results.csv`.

## Run one build

The shortest path from a fresh clone to one measured run, using
Antigravity CLI (`agy`) as the example. [RUNNING.md](RUNNING.md) has
the full detail behind every step, and Claude Code and Gemini CLI setup.
Commands run from this folder unless they say otherwise.

### 1. One-time machine setup

```bash
brew install colima docker docker-compose ripgrep
```

- Android SDK at `~/Library/Android/sdk` with an AVD such as Pixel 4 XL.
- JDK 21 on the `PATH`.
- Antigravity CLI, installed per
  https://antigravity.google/docs/cli/reference. Then run `agy install`,
  launch `agy` once from the repo root to log in and trust the folder,
  and use `agy models` to list the model ids the runner accepts.

Keep the agents' global instruction files empty, or the runner refuses
to start. The list is in RUNNING section 1, "Instruction file audit".

### 2. Build the starting projects (once per clone)

```bash
cd harness
./setup-templates.sh
(cd templates/cold && ./gradlew -q :app:assembleDebug)   # warm the Gradle cache
(cd templates/ohs  && ./gradlew -q :app:assembleDebug)
```

After editing anything in `skills/`, run `./refresh-skills-templates.sh`.

### 3. Every sitting

```bash
colima start
~/Library/Android/sdk/emulator/emulator -avd Pixel_4_XL &
adb devices        # exactly one device must be listed
caffeinate -is &   # keep the machine awake
```

The test FHIR server needs about 1 GB of Docker memory. If other
containers fill Docker's memory, stop them first, or the server is killed
(exit 137) and the run stops with "seed load failed".

### 4. Run one build

```bash
cd harness
./runner.sh antigravity gemini-3.8-flash-medium ohs-skills 100   # pick an unused replicate
```

The format is `./runner.sh <agent> <model> <condition> <replicate>`.

| Part | Values |
|---|---|
| agent | `claude`, `gemini`, `antigravity` |
| model | Claude: `<model id>-<effort>`, e.g. `claude-opus-5-5-medium`. Antigravity: an id from `agy models`, e.g. `gemini-3.8-flash-medium`. Gemini CLI: a plain id, e.g. `gemini-3.8-flash` |
| condition | `cold`, `fhir`, `ohs`, `ohs-skills` |
| replicate | any number not used before for that model and condition |

The harness resets and seeds the FHIR server, runs the agent, builds the
app, and saves everything to `runs/s1-<condition>-<model>-<replicate>/`
plus one row in `results.csv`. To run several builds, list them in a
manifest (one `<agent> <model> <condition> <replicate>` per line) and run
`./campaign.sh <manifest>`. Finished builds are skipped on a rerun.

### 5. Next

- **Read the run's output.** [runs/README.md](runs/README.md) explains
  each file and each `results.csv` column.
- **Score the app** on the 10 checks with the scripts in
  [harness/walk/](harness/walk/README.md).
- **A run stopped with "HARNESS FAULT".** Fix the cause it names, then
  see RUNNING section 6.
- **A new model.** Do one throwaway probe first (RUNNING, "First gemini
  or antigravity run only"). A model missing from the price table
  records tokens but no cost (RUNNING section 8).

## Layout

| Path | What it is |
|---|---|
| `docker-compose.yml`, `hapi-extra.yaml` | HAPI FHIR R4 server with request validation on |
| `seed/`, `load-seed.sh` | Sample ANC patients and the visit Questionnaire |
| `build-*-prompt.md` | The verbatim prompt for each condition |
| `skills/` | Agent skills for the three OHS libraries |
| `harness/` | The run automation (runner, campaign, extractors, templates) |
| `runs/` | One folder per run with transcript, metrics and code diff |
| `results.csv` | One row per run |
| `results/` | Scores, charts and the chart script |
| `docs/` | The blog and the experiment design |
