# ANC PoC — "App Is the IG" experiment

Tests the claim from [Health Samurai's "FHIR as a framework for agentic
coding"](https://www.health-samurai.io/articles/fhir-as-a-framework-for-agentic-coding)
on the OHS stack: give a coding agent the same app spec with and without
FHIR Foundations (HAPI + kotlin-fhir + FHIR Engine + Data Capture) and
compare what it builds. Grew from a single two-build experiment into a
model × condition evaluation grid with an automated harness.

See `../ohs-player-reference-client-app/app-is-the-ig-ohs-agent-experiment-simple.md`
for the original PoC brief.

## Layout

| Path | What it is |
|---|---|
| `docker-compose.yml`, `hapi-extra.yaml` | HAPI FHIR R4 server, request validation on |
| `seed/anc-seed-bundle.json`, `load-seed.sh` | 3 patients, 3 encounters, 12 observations, the `anc-contact` Questionnaire |
| `docs/protocol.md` | The protocol: Part A original two-build experiment, Part B the eval grid and demonstrations |
| `build-a-prompt.md`, `build-b-prompt.md` | The verbatim opening prompts (cold / OHS conditions) |
| `skills/` | Agent skills for the three OHS libraries (kotlin-fhir, engine, data capture) — evidence-based, library-docs-only |
| `harness/` | Automated run infrastructure: `runner.sh` (one clean run), `campaign.sh` + `manifest.txt` (the full grid), `extract.py` (metrics + transcript rendering), `templates/` (pristine scaffolds per condition) |
| `runs/` | One folder per run: `transcript.{jsonl,md}`, `run.json`, `code.diff`, `launch.png` — see `runs/README.md` for naming |
| `results.csv` | One scorecard row per run (regenerable from the `run.json` files) |
| `results/grid.md` | Current results grid: status, cost, minutes, tokens per model x condition |
| `results/experiment-1.md` | The original two-build experiment report (frozen) |
| `docs/harness.md` | Harness design: the grid, cleanliness contract, failure policy |
| `docs/demo.md` | Plan for the demo video (build time-lapse) |

**Full start-to-finish instructions, including how every run's artifacts
(`transcript.jsonl`, `transcript.md`, `run.json`, `code.diff`) are
produced: see [RUNNING.md](RUNNING.md).**

## Run the server

```bash
colima start          # docker daemon runs in colima on this machine
docker-compose up -d  # standalone docker-compose; the `docker compose` plugin isn't installed
./load-seed.sh
```

Check: <http://localhost:8080/fhir/Patient> lists Emily Carter, Sarah
Mitchell, Grace Thompson. From the Android emulator the server is
`http://10.0.2.2:8080/fhir` (plain HTTP — cleartext config needed).

Data lives in the container: `docker-compose down` wipes it; re-run
`./load-seed.sh` after bringing it back up. The eval harness resets and
reseeds it before every run automatically.

## Run the evaluation

Prereqs: emulator booted, colima up, machine kept awake.

```bash
cd harness
./runner.sh <condition> <model> <replicate>   # one run, e.g.: ./runner.sh ohs opus 02
./campaign.sh                                  # or: walk manifest.txt, skipping completed runs
```

Conditions: `cold` (scratch), `ohs` (Foundations libraries),
`ohs-skills` (Foundations + `skills/`). Models: `haiku`, `sonnet`,
`opus`, `fable`. Every run is hermetic — fresh scaffold directory (new
Claude project, no session/memory bleed), server reset + reseed, device
uninstall sweep, previous work dirs archived out of sight. Runs that hit
environment faults (network, subscription usage limit) are discarded and
halt the campaign; agent failures are kept as data. After each run, the
app still needs a human "verified working" walk (launch, data visible,
record a visit) — the smoke check alone has been fooled twice.

## Status (as of 2026-08-31)

Sweep 1 complete: all 12 cells (4 models × 3 conditions) have one run;
grid + takeaways in `results/grid.md`. Headlines so far: every model
ships a working cold app; the OHS stack needs Sonnet-class capability or
better (both Haiku runs broke); the skills cut Fable's OHS build 4× and
Opus's 2.5×; cheapest reliable OHS build today is Opus + skills (~$11,
~14 min). Replicate sweeps (manifest entries 02/03) still to run.
