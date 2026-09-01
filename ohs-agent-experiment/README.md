# OHS agent experiment

## What this is trying to do

We want to know if the OHS FHIR libraries make AI coding agents build
better health apps. The idea comes from a [Health Samurai
article](https://www.health-samurai.io/articles/fhir-as-a-framework-for-agentic-coding)
which claimed that agents build more coherent apps on a FHIR stack. They
showed it with impressions only. This experiment tests the same claim on
the OHS stack with real measurements. The original one-page brief lives
in the reference app repo as `app-is-the-ig-anc-poc-simple.md`.

## How we test it

An AI agent gets the same ANC app spec and builds it under three
conditions.

1. Cold. An empty project. The agent picks its own stack and storage.
2. OHS. The project has kotlin-fhir, FHIR Engine, and Data Capture on the
   classpath, plus a HAPI FHIR server to sync with.
3. OHS plus skills. Same as OHS, with our agent docs for the three
   libraries added to the project.

Each condition runs across several models (Haiku, Sonnet, Opus, Fable,
and optionally Gemini models) and is repeated for reliability. An
automated harness gives every run a clean slate. Fresh session, fresh
folder, reset server, wiped device.

## What we measure

1. Does the app actually work. A human installs and uses every app,
   because broken apps can look finished.
2. Cost and time per working app.
3. What the app is worth afterward. Cold builds store data in made-up
   formats locked on the phone. OHS builds store standard FHIR on a
   server where any health system can read it.

## Results so far

Sweep 1 is complete. All 12 cells have one run each. See
[results/grid.md](results/grid.md). Highlights

1. Every model ships a working cold app. Building an app is not the hard
   part anymore.
2. The OHS stack needs a capable model. Both Haiku runs broke.
3. The skills docs cut the OHS build cost 4x for Fable and 2.5x for Opus.
4. Cheapest reliable OHS build today is Opus plus skills at about 11
   dollars in about 14 minutes.

Replicate sweeps are still to run. Treat sweep 1 as signal, not proof.

## Layout

| Path | What it is |
|---|---|
| `docker-compose.yml`, `hapi-extra.yaml` | HAPI FHIR R4 server with request validation on |
| `seed/`, `load-seed.sh` | Sample ANC patients and the visit Questionnaire |
| `build-a-prompt.md`, `build-b-prompt.md` | The verbatim prompts for the cold and OHS conditions |
| `docs/protocol.md` | The experiment rules and the eval grid |
| `docs/harness.md` | Harness design and the per-run cleanliness contract |
| `docs/demo.md` | Plan for the demo video |
| `skills/` | Agent docs for the three OHS libraries |
| `harness/` | The run automation (runner, campaign, extractors, templates) |
| `runs/` | One folder per run with transcript, metrics, and code diff |
| `results.csv` | One scorecard row per run |
| `results/grid.md` | Current results grid |
| `results/experiment-1.md` | Report of the original two-build experiment |
| `RUNNING.md` | Full start-to-finish instructions |

## Quick start

Bring up the server

```bash
colima start
docker-compose up -d
./load-seed.sh
```

Run one build (emulator must be booted)

```bash
cd harness
./runner.sh claude opus ohs 02
```

Or walk a whole grid with `./campaign.sh manifest-claude.txt` (one
manifest per agent). Everything else, including
supported models, artifact collection, and Gemini setup, is in
[RUNNING.md](RUNNING.md).
