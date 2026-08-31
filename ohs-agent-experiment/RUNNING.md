# Running the experiment, start to finish

Every step from a fresh machine sitting to a scored run, including where
each artifact (`transcript.jsonl`, `transcript.md`, `run.json`,
`code.diff`) comes from. Two paths: the **harness** (automated, used for
the eval grid) and the **manual** path (interactive sessions, used for
the original two-build experiment) — the artifacts are identical either
way.

## 0. Prerequisites (once per machine)

- **Docker via colima** with standalone `docker-compose` (the
  `docker compose` plugin is not installed here):
  `brew install colima docker docker-compose`
- **Android SDK** at `~/Library/Android/sdk` with an AVD (Pixel 4 XL),
  and JDK 21 on the PATH.
- **Claude Code** logged in. Note for scripts: `claude` is a zsh alias
  on this machine; scripts must call the real binary at
  `~/.local/bin/claude` (runner.sh does).
- **Templates** in `harness/templates/` — pristine scaffold repos, one
  per condition. If missing, recreate: clone the baseline commit of
  `../../anc-build-a-cold` (cold) or `../../anc-build-b-foundations` (ohs)
  into the template dir, strip `.git`, re-init, commit once; for
  `ohs-skills`, copy `skills/{kotlin-fhir,kotlin-fhir-engine,kotlin-fhir-data-capture}`
  into the template's `.claude/skills/` and commit.
- **One-time fairness prep**: run a throwaway `./gradlew :app:assembleDebug`
  in each template so the shared Gradle cache is warm for every run,
  and check `~/.claude/CLAUDE.md` contains nothing that could coach the
  runs (must be empty or neutral; it's constant across cells either way).

## 1. Per-sitting startup

```bash
colima start
~/Library/Android/sdk/emulator/emulator -avd Pixel_4_XL &   # wait for home screen
~/Library/Android/sdk/platform-tools/adb get-state          # must print "device"
caffeinate -is &                                             # keep the machine awake
```

The harness resets and reseeds HAPI itself before every run; no manual
server prep needed. (For anything else, `docker-compose up -d &&
./load-seed.sh` from the project root brings the server up seeded.)

## 2. Run — harness path (the eval grid)

```bash
cd harness
./runner.sh <condition> <model> <replicate>   # one run, e.g. ./runner.sh ohs opus 02
./campaign.sh                                  # or walk manifest.txt (skips completed runs)
```

Conditions `cold | ohs | ohs-skills`; models `haiku | sonnet | opus | fable`.

What one run does, in order (all automated by `runner.sh`):

1. **Preflight**: refuses to start if `runs/<run_id>` exists, no
   emulator, no API connectivity, `work/` isn't empty, or a Claude
   project dir already exists for the work path (context-cleanliness
   assertions).
2. **Fresh scaffold**: clones the condition's template into
   `harness/work/<run_id>/` — a never-used path, so the agent gets an
   empty Claude project (no session, no memory) — and writes
   `local.properties`.
3. **Server reset**: `docker-compose down && up -d` + `load-seed.sh`
   (verified counts: 3 patients / 3 encounters / 12 observations /
   1 questionnaire). Runs for cold too, so the environment is constant.
4. **Device reset**: uninstalls every `com.example.*` package; aborts
   if anything survives.
5. **Agent run**: pipes the condition's prompt (everything below the
   `---` in `build-a-prompt.md` or `build-b-prompt.md`, verbatim) into
   headless Claude Code with the chosen model, permissions bypassed,
   60-minute wall-clock cap.
6. **Environment-fault gate**: a run with zero tool calls, or one cut
   off by the subscription usage limit, is discarded and halts the
   campaign — those are not data. Agent failures (broken app within
   caps) are kept; they ARE data.
7. **Smoke check**: `assembleDebug`, install, launch, screenshot to
   `runs/<run_id>/launch.png`. Smoke pass means "launches", nothing
   more — it has been fooled by broken apps twice.
8. **Artifact export** (the four files, into `runs/<run_id>/`):
   - `code.diff` — the run's work is committed in the work clone, then
     `git diff <baseline> HEAD` captures everything the agent changed.
   - `transcript.jsonl` — copied from the run's Claude project dir
     (`~/.claude/projects/<dashed-work-path>/`, newest `.jsonl`).
   - `transcript.md` — rendered FROM the jsonl by `extract.py`
     (headless runs can't `/export`).
   - `run.json` — filled by `extract.py`: wall clock, turns, tool
     calls, build failures, `OperationOutcome` incidents, token sums,
     cost at the model's API rates, diff size. `verified_working` and
     `round_trip_pass` stay null for the human walk.
   Plus one row appended to `results.csv`. A run folder missing any of
   the four is incomplete — fix before the next run.
9. **Teardown**: work dir moved to `harness/archive/<run_id>` (so the
   next agent can't find a previous solution on disk), device swept
   again.

## 3. Run — manual path (interactive session)

For runs driven by hand (original docs/protocol.md Part A experiment, scenario
sessions):

1. Fresh scaffold dir, seeded server, clean device — same as above,
   by hand.
2. `cd <scaffold> && claude`, paste the prompt verbatim, drive per the
   operator rules in `docs/protocol.md` (product-owner answers only, errors
   pasted verbatim).
3. Export the artifacts:

```bash
RUN=runs/<run_id>; mkdir -p $RUN
# transcript.md - from inside the session before closing:
#   /export ../ohs-labs/ohs-agent-experiment/runs/<run_id>/transcript.md
# transcript.jsonl - newest session file for that project dir:
cp "$(ls -t ~/.claude/projects/<dashed-scaffold-path>/*.jsonl | head -1)" $RUN/transcript.jsonl
# code.diff - from the scaffold repo:
git -C <scaffold> add -A && git -C <scaffold> commit -m "<run_id> result"
git -C <scaffold> diff <baseline-commit> HEAD > $RUN/code.diff
# run.json + results.csv row (also re-renders transcript.md if you skipped /export):
python3 harness/extract.py --jsonl $RUN/transcript.jsonl --run-dir $RUN \
  --run-id <run_id> --condition <cond> --model <model> --replicate <n> \
  --results results.csv
```

## 4. After the run: the human walk (mandatory)

For every run, install the built APK (in
`harness/archive/<run_id>/app/build/outputs/apk/debug/`), launch it,
and check: register shows the three patients (for ohs conditions this
proves sync), record a visit, force-stop and relaunch (visit survives),
and for ohs conditions confirm the visit reached HAPI
(`http://localhost:8080/fhir/QuestionnaireResponse?_sort=-_lastUpdated`).
Then record the verdict in `runs/<run_id>/run.json`
(`verified_working`, `round_trip_pass`, one-line `notes` for anything
interesting) and mirror it into that run's `results.csv` row.

## 5. Interruptions and cleanup

- **Usage limit / network**: the campaign halts itself with a message;
  rerun `./campaign.sh` after the limit resets — completed runs are
  skipped automatically.
- **A junk run slipped through**: delete `runs/<id>`,
  `harness/archive/<id>`, `harness/logs/<id>.log`, the
  `~/.claude/projects/<dashed>` dir, and its `results.csv` row; the
  campaign will redo it.
- `results.csv` is derived — if in doubt, regenerate it from the
  `run.json` files.

## 6. Reading the results

`results.csv` is one row per run; `results/grid.md` holds the current
grid and takeaways; each `runs/<id>/transcript.md` is the quotable
record and `transcript.jsonl` the parseable one.
