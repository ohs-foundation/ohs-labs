# Running the experiment

Every step from a fresh machine to a scored run. Covers all three agents
(Claude Code, Gemini CLI, Antigravity CLI) and explains where each
artifact comes from. Why the harness works this way is in
`docs/design.md`.

## 1. One-time machine setup

**Docker.** Install colima and standalone docker-compose with
`brew install colima docker docker-compose`. The `docker compose`
plugin form is not used here.

**Android.** SDK at `~/Library/Android/sdk` (or set `ANDROID_HOME`)
with an AVD such as Pixel 4 XL. JDK 21 on the PATH.

**Claude Code.** Log in once. Scripts call the real binary at
`~/.local/bin/claude` because `claude` is only a shell alias.

**Gemini CLI** (only for gemini runs). Install with
`npm i -g @google/gemini-cli` and set `GEMINI_API_KEY`. Personal Google
login no longer works: as of 2026-10-12 the free Code Assist tier rejects
gemini-cli ("This client is no longer supported... migrate to the
Antigravity suite").

**Gemini CLI may swap the model.** gemini-cli 0.60 can quietly replace
the model you ask for: any name ending in `flash` (e.g.
`gemini-3.8-flash`) is sent as `gemini-3.5-flash`. To get the model you
asked for, add this to `~/.gemini/settings.json`:

```json
{ "experimental": { "dynamicModelConfiguration": true } }
```

It does not help for `gemini-2.5-flash`, which is still swapped. To see
which model answered a run, see section 8.

**Antigravity CLI** (only for antigravity runs). Install `agy` per
`https://antigravity.google/docs/cli/reference`, run `agy install`, then
log in once by launching `agy` interactively (it uses Google OAuth, and its state
lives in `~/.gemini/antigravity-cli/`, separate from Gemini CLI's).
`agy models` lists the ids the runner accepts. The harness `work/` dir
must sit under a trusted workspace: `trustedWorkspaces` in
`~/.gemini/antigravity-cli/settings.json` should list this repo's parent
(`ohs-labs`), which the first interactive launch from there records.

**Ripgrep** (optional). `brew install ripgrep`. The agent CLIs use it
for code search when present.

**Git.** Nothing to configure. The runner sets a neutral identity
(`OHS Agent <agent@example.com>`) and uses `--no-ext-diff`, so your own
git config cannot affect a run.

**Templates.** The pristine starting projects live in
`harness/templates/` and are not tracked in git. Build them once from
the committed sources

```bash
cd harness
./setup-templates.sh
```

There are six. `cold`, `fhir` and `ohs` are shared by every agent. The skills
template is per agent: `ohs-skills-claude`, `ohs-skills-gemini`, and
`ohs-skills-antigravity`.

**After editing any skill** in `skills/`, rebuild the three skills templates
so the runner picks it up (editing `skills/` alone does not reach a run):

```bash
cd harness
./refresh-skills-templates.sh
```

That is a skill/treatment change, so add a version to `skills/CHANGELOG.md` and do not
pool the new ohs-skills runs with older ones.

**Cache warming.** Run one throwaway build in `templates/cold` and one
in `templates/ohs` so the shared Gradle cache is equally warm for every
measured run

```bash
(cd templates/cold && ./gradlew -q :app:assembleDebug)
(cd templates/ohs && ./gradlew -q :app:assembleDebug)
```

**Instruction file audit.** Agents load global instruction files into
every session, so keep these empty or absent, or a run gets coached.
The runner refuses to start a gemini or antigravity run otherwise (why:
`docs/design.md` section 7).

- `~/.claude/CLAUDE.md`
- `~/.gemini/GEMINI.md`
- `~/.gemini/config/` must not hold `rules/`, `skills/`, `GEMINI.md` or
  `AGENTS.md`
- `~/.gemini/antigravity-cli/knowledge/` must be empty

## 2. Every sitting

```bash
colima start
~/Library/Android/sdk/emulator/emulator -avd Pixel_4_XL &
~/Library/Android/sdk/platform-tools/adb devices     # exactly one device must be listed
caffeinate -is &                                     # keep the machine awake
```

The harness resets and reseeds the HAPI server before every run, so no
manual server preparation is needed. To bring the server up for
anything else, run `docker-compose up -d && ./load-seed.sh` from the
project root.

## 3. Run with the harness

One run

```bash
cd harness
./runner.sh <agent> <model> <condition> <replicate>
./runner.sh claude claude-opus-5-5-medium ohs 1   # example
./runner.sh gemini gemini-3.1-pro cold 1     # example
./runner.sh antigravity gemini-3.8-flash-high cold 1   # example
```

A whole grid. One manifest per agent, always named explicitly

```bash
./campaign.sh manifest-claude.txt
./campaign.sh manifest-gemini.txt
./campaign.sh manifest-antigravity.txt
```

The conditions are `cold`, `fhir`, `ohs` and `ohs-skills`, described in
`README.md`. The campaign skips
runs that already exist, so it resumes cleanly after any interruption.

### What one run does

1. **Preflight.** Refuses to start if the run already exists, no
   emulator is connected, the agent API is unreachable, the work area
   is not empty, or leftover agent state exists for the work path (for
   antigravity: a conversation already recorded for the work path in
   `~/.gemini/antigravity-cli/cache/last_conversations.json`).
2. **Fresh scaffold.** Clones the right template (picked from condition
   plus agent) into a never-used folder. A new folder means the agent
   starts with no session history and no memory.
3. **Server reset.** Recreates and reseeds HAPI, for cold runs too, so
   the environment is constant.
4. **Device reset.** Uninstalls every `com.example.*` package and
   verifies the device is clean.
5. **Agent run.** Pipes the condition prompt (the text below the `---`
   in the condition's `build-*-prompt.md`, verbatim) into the
   agent headless, permissions auto-approved, capped at 60 minutes.
   Antigravity only: when agy ends its turn while waiting on a
   background command, the runner resumes the conversation with a
   neutral continue prompt, at most 12 times within the 60-minute cap,
   and counts the resumes as `resume_turns` (why: `docs/design.md`
   section 7).
6. **Fault gate.** The run is an environment fault if the agent made
   zero tool calls, or if a usage or quota limit cut it off. A faulted run is
   discarded and the campaign halts. An agent that finishes with a
   broken app is kept, because that is data. An empty `code.diff` is
   also kept as data, flagged `EMPTY DIFF` in the log and
   `run.json.notes`.
7. **Smoke check + verification.** The runner builds, installs, clears
   the logcat buffers and launches. Then `verify.sh` gives sync ~30s, screenshots
   the settled screen to `launch.png`, detects a crash from the crash
   buffer, captures `logcat.txt` (and `crash.txt` if any), and does a
   best-effort count of how many patients reached the app's local DB.
   It writes `verification.json` (folded into `run.json`). The smoke
   verdict is launched-without-crash, and `patients_in_local_db` is the
   automated sync-success signal (0 or null means download sync did not
   deliver - it catches the "sync never wired" failure the old
   launch-only check passed). Whether the register visually renders is
   still the human walk, judged from the post-sync `launch.png`.
8. **Artifact export.** The run's files land in `runs/<run_id>/`, plus
   one `results.csv` row. The extractor reports the folder as
   incomplete if `transcript.jsonl`, `transcript.md`, `run.json` or
   `code.diff` is missing. What each file is and where it comes from is
   in `runs/README.md`. The two walk verdicts in `run.json` stay null
   until section 5.

9. **Teardown.** The work folder is archived away so the next agent
   cannot find a previous solution, the device is swept again, and any
   memory a Gemini agent saved globally is moved into the run folder
   (details in `docs/design.md` section 7).

### First gemini or antigravity run only

Run one probe and eyeball it before trusting that agent's metrics

```bash
./runner.sh gemini gemini-3.1-pro cold 99
./runner.sh antigravity gemini-3.8-flash-high cold 99
```

Open the probe's `transcript.jsonl` and check its `run.json` looks
sane. The gemini stream format was verified against gemini-cli v0.57.0
and the antigravity one against agy v1.2.7. A newer CLI could change
either. For antigravity also confirm the app landed in the work folder
and not in `~/.gemini/antigravity-cli/scratch/` (the runner passes
`--add-dir` for exactly this reason). Delete the probe folder and its
`results.csv` row afterward.

## 4. Run manually (interactive session)

For hand-driven runs outside the harness.

1. Prepare a fresh scaffold folder, seeded server, and clean device by
   hand, as in the harness steps above.
2. Start the agent in the scaffold folder, paste the prompt verbatim,
   and follow the run rules in `docs/design.md` section 3. Answer product
   questions only and paste errors verbatim.
3. Export the artifacts

```bash
RUN=runs/<run_id>
mkdir -p $RUN
# transcript.md  (from inside the session, before closing)
#   /export ../ohs-labs/ohs-agent-experiment/runs/<run_id>/transcript.md
# transcript.jsonl
cp "$(ls -t ~/.claude/projects/<work-path>/*.jsonl | head -1)" $RUN/transcript.jsonl
# code.diff
git -C <scaffold> add -A && git -C <scaffold> commit -m "<run_id> result"
git -C <scaffold> diff <baseline-commit> HEAD > $RUN/code.diff
# run.json and the results row
python3 harness/extract-claude.py --jsonl $RUN/transcript.jsonl --run-dir $RUN \
  --run-id <run_id> --condition <cond> --model <model> --replicate <n> \
  --results results.csv
```

## 5. The human walk (mandatory, per run)

Install the built APK from
`harness/archive/<run_id>/app/build/outputs/apk/debug/` and use the
app. This step exists because two broken apps passed every automated
check.

**Basic walk.** The register shows the three patients, a new visit
saves, and it survives a force-stop and relaunch. For FHIR apps the
visit also reaches the server. Apps store a visit as different resource
types, so check whichever the app writes, e.g.
`http://localhost:8080/fhir/Observation?_sort=-_lastUpdated` or
`.../Encounter`, `.../QuestionnaireResponse`. Query the server with
`Cache-Control: no-cache`, because HAPI caches searches for about a
minute. Record `verified_working` and `round_trip_pass` in the run's
`run.json` and its `results.csv` row, plus a one-line note for anything
interesting.

**Score out of 10.** The 10 checks used in the blog and how to test
each one are in `results/app-scores.md`, using the scripts in
`harness/walk/`. Add the new app's scores there.

## 6. When things go wrong

**Usage or quota limit.** The campaign halts itself with a clear
message. Rerun `./campaign.sh <manifest>` after the limit resets and it
continues where it stopped.

**Antigravity quota.** agy runs on your Antigravity subscription, not
an API key, and it has a per-model quota that resets on a short timer
(the error names it, e.g. "Individual quota reached. Resets in 12m45s").
The gate discards the run as a fault, the campaign halts, and rerunning
after the reset continues where it stopped. A campaign of `-high` runs
can hit this several times a day. `-medium` or `-low` spend it slower.

**"seed load failed" or the server exits with code 137.** Docker ran
out of memory and killed the FHIR server. It needs about 1 GB. Stop
other containers, then rerun.

**Rerunning an antigravity run.** Antigravity remembers every work
folder it has seen. If the agent had already started, rerun with a new
replicate number, or the preflight refuses the old one.

**A leftover `harness/work/<id>` with no `.git`.** That is not a run, it
is build output a Gradle daemon wrote back after the runner discarded
the folder. The runner now stops the project's daemons before a discard
and removes such husks itself at preflight. Deleting the folder by hand
is also safe.

**A junk run got collected.** Delete `runs/<id>`,
`harness/archive/<id>`, `harness/logs/<id>.log`, the leftover agent
state for the work path, and the run's `results.csv` row. The campaign
will redo it.

**results.csv looks wrong.** The `run.json` files are the source of
truth. Fix the row by hand from them. There is no regeneration script.

## 7. Reading the results

`results.csv` has one row per run. `results/app-scores.md`
holds the 10-check scores, and `docs/blog-interoperability-tax.md` the
write-up. `README.md` lists which runs the blog uses. Each run's `transcript.md` is the readable record
and `transcript.jsonl` the parseable one.

## 8. Supported models

| Agent | Model argument | Notes |
|---|---|---|
| claude | `claude-fable-5-1-<effort>` | $10/$50 per MTok, cache reads 0.025x input |
| claude | `claude-opus-5-5-<effort>` | $4/$20, cache reads 0.05x input |
| claude | `claude-sonnet-5-5-<effort>` | $2/$10, cache reads 0.05x input |
| claude | `claude-haiku-5-5-<effort>` | $0.10/$0.50, 5x for any request whose prompt is over 100K tokens |
| gemini | `gemini-3.8-flash`, `3.7-flash`, `3.6-flash` | $0.75/$3.75, intro rate through 2026-12-31, then $1.50/$7.50 |
| gemini | `gemini-3-flash` | $0.50/$3 |
| gemini | `gemini-3.1-pro` | $2/$12 |
| gemini | `gemini-4-argon` | $2/$10 |
| gemini | `gemini-2.5-pro` | $1.25/$10, previous generation |
| gemini | `gemini-2.5-flash` | $0.30/$2.50, swapped for 3.5 Flash even with the setting |
| antigravity | `gemini-3.8-flash-high` | Gemini 3.8 Flash driven by `agy`. `-low`/`-medium`/`-high` is the reasoning effort |
| antigravity | any other `gemini-*-{low,medium,high}` from `agy models` | e.g. `gemini-3.7-flash-medium`, `gemini-3.1-pro-high` |

Rates live in `GEMINI_RATES` (`harness/extract-gemini.py`), gathered
2026-09-01. Spot-check before quoting externally.

Claude takes a model id plus a Claude Code effort level (`low`,
`medium`, `high`, `xhigh` or `max`), e.g. `claude-opus-5-5-medium`. The
runner passes the effort as `--effort`. Claude rates live in `RATES`
(`harness/extract-claude.py`), checked 2026-10-13. Cache writes are
billed at 2x input because Claude Code uses the 1-hour cache. Gemini accepts any name that
starts with `gemini`. Antigravity accepts any `gemini-*` id that
`agy models` prints with an effort suffix. It also offers Claude and
GPT-OSS models, which the runner rejects. Antigravity strips the
suffix for pricing, so `gemini-3.8-flash-high` is priced as
`gemini-3.8-flash`. A name missing from `GEMINI_RATES` still runs but
reports a null cost.

**Which model answered.** `run.json.model_served` records it for
gemini and antigravity runs. Gemini CLI: per-model usage from the
stream's final stats (expect about 1% on `gemini-3-flash-preview`,
which gemini-cli uses for its own checks). Antigravity: calls per model
from agy's conversation db, because the stream itself only echoes the request.
Every Antigravity run so far was answered by the model it asked for.

Gemini CLI's `output_tokens` also excludes thinking tokens (it reports
`candidates` only, while `thoughts` appear per turn in
`~/.gemini/tmp/<project>/chats/*.jsonl` but not in the stream), so gemini
cost is a floor on the output side. Antigravity's `output_tokens`
includes thinking.

How a run id tells Gemini CLI and Antigravity runs apart is in
`runs/README.md`.
