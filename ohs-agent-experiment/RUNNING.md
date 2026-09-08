# Running the experiment

Every step from a fresh machine to a scored run. Covers both agents
(Claude and Gemini) and explains where each artifact comes from.

## 1. One-time machine setup

**Docker.** Install colima and standalone docker-compose with
`brew install colima docker docker-compose`. The `docker compose`
plugin form is not used here.

**Android.** SDK at `~/Library/Android/sdk` (or set `ANDROID_HOME`)
with an AVD such as Pixel 4 XL. JDK 21 on the PATH.

**Claude Code.** Log in once. Scripts call the real binary at
`~/.local/bin/claude` because `claude` is only a shell alias.

**Gemini CLI** (only for gemini runs). Install with
`npm i -g @google/gemini-cli`, then authenticate by setting
`GEMINI_API_KEY` or configuring an auth method in
`~/.gemini/settings.json`.

**Ripgrep.** Install `ripgrep` (e.g., `brew install ripgrep` on macOS). Although not strictly required, having it installed allows the agent CLI to execute extremely fast codebase searches during the runs instead of falling back to standard grep.

**Git.** The harness automatically handles Git environment setups. It exports a neutral Git author and committer identity (`OHS Agent <agent@example.com>`) and forces built-in diffs (`--no-ext-diff`) to bypass local sandbox and git config restrictions seamlessly.

**Templates.** The pristine starting projects live in
`harness/templates/` and are not tracked in git. Build them once from
the committed sources

```bash
cd harness
./setup-templates.sh
```

There are four. `cold` and `ohs` are shared by both agents. The skills
template is per agent, `ohs-skills-claude` and `ohs-skills-gemini`.

**After editing any skill** in `skills/`, rebuild the two skills templates
so the runner picks it up (editing `skills/` alone does not reach a run):

```bash
cd harness
./refresh-skills-templates.sh
```

That is a skill/treatment change, so bump `skills/README.md` and do not
pool the new ohs-skills runs with older ones.

**Cache warming.** Run one throwaway build in `templates/cold` and one
in `templates/ohs` so the shared Gradle cache is equally warm for every
measured run

```bash
(cd templates/cold && ./gradlew -q :app:assembleDebug)
(cd templates/ohs && ./gradlew -q :app:assembleDebug)
```

**Instruction file audit.** `~/.claude/CLAUDE.md` and
`~/.gemini/GEMINI.md` are injected into every session of their agent.
Both must be empty or absent so no run gets coached. The runner also
refuses to start a gemini run while a non-empty `~/.gemini/GEMINI.md`
exists.

## 2. Every sitting

```bash
colima start
~/Library/Android/sdk/emulator/emulator -avd Pixel_4_XL &
~/Library/Android/sdk/platform-tools/adb get-state   # must print "device"
caffeinate -is &                                     # keep the machine awake
```

The harness resets and reseeds the HAPI server before every run, so no
manual server preparation is needed. To bring the server up for
anything else, run `docker-compose up -d && ./load-seed.sh` from the
project root.

## 3. Supported models

| Agent | Model argument | Notes |
|---|---|---|
| claude | `fable` | claude-fable-5, $10/$50 per MTok |
| claude | `opus` | claude-opus-5, $5/$25 |
| claude | `sonnet` | claude-sonnet-5, $2/$10 |
| claude | `haiku` | claude-haiku-4-5-20251001, $1/$5 |
| gemini | `gemini-3.7-flash` | current workhorse, $0.75/$3.75 intro until 2027 then $1.50/$7.50 |
| gemini | `gemini-3.6-flash` | same intro pricing schedule |
| gemini | `gemini-3-flash` | $0.50/$3 |
| gemini | `gemini-3.1-pro` | $2/$12 |
| gemini | `gemini-2.5-pro` | $1.25/$10, previous generation |
| gemini | `gemini-2.5-flash` | $0.30/$2.50 |

Claude accepts only the four shortcuts. Gemini accepts any name that
starts with `gemini`, passed through raw. The six listed have pricing
wired in `GEMINI_RATES` inside `harness/extract-gemini.py`. Any other
name still runs but reports a null cost until a rate is added there.
Prices gathered 2026-09-01, spot-check before quoting externally.

## 4. Run with the harness

One run

```bash
cd harness
./runner.sh <agent> <model> <condition> <replicate>
./runner.sh claude opus ohs 02                # example
./runner.sh gemini gemini-3.7-flash cold 01   # example
```

A whole grid. One manifest per agent, always named explicitly

```bash
./campaign.sh manifest-claude.txt
./campaign.sh manifest-gemini.txt
```

Conditions are `cold` (empty project), `ohs` (OHS libraries plus
server), and `ohs-skills` (ohs plus the agent docs). The campaign skips
runs that already exist, so it resumes cleanly after any interruption.

### What one run does

1. **Preflight.** Refuses to start if the run already exists, no
   emulator is connected, the agent API is unreachable, the work area
   is not empty, or leftover agent state exists for the work path.
2. **Fresh scaffold.** Clones the right template (picked from condition
   plus agent) into a never-used folder. A new folder means the agent
   starts with no session history and no memory.
3. **Server reset.** Recreates and reseeds HAPI, for cold runs too, so
   the environment is constant.
4. **Device reset.** Uninstalls every `com.example.*` package and
   verifies the device is clean.
5. **Agent run.** Pipes the condition prompt (the text below the `---`
   in `build-a-prompt.md` or `build-b-prompt.md`, verbatim) into the
   agent headless, permissions auto-approved, capped at 60 minutes.
6. **Fault gate.** A run with zero tool calls, or one cut off by a
   usage or quota limit, is an environment fault. It is discarded and
   the campaign halts. An agent that finishes with a broken app is
   kept, because that is data.
7. **Smoke check + verification.** Builds, installs, launches, then
   `verify.sh` clears the logcat buffers, gives sync ~30s, screenshots
   the settled screen to `launch.png`, detects a crash from the crash
   buffer, captures `logcat.txt` (and `crash.txt` if any), and does a
   best-effort count of how many patients reached the app's local DB.
   It writes `verification.json` (folded into `run.json`). The smoke
   verdict is launched-without-crash; `patients_in_local_db` is the
   automated sync-success signal (0 or null means download sync did not
   deliver - it catches the "sync never wired" failure the old
   launch-only check passed). Whether the register visually renders is
   still the human walk, judged from the post-sync `launch.png`.
8. **Artifact export.** Four files land in `runs/<run_id>/` plus one
   results row. A folder missing any of the four is incomplete.

   | File | Where it comes from |
   |---|---|
   | `transcript.jsonl` | Claude runs copy the session file from `~/.claude/projects/<work-path>/`. Gemini runs capture the CLI stream-json stdout directly. |
   | `transcript.md` | Rendered from the jsonl by the agent's extractor, `extract-claude.py` or `extract-gemini.py`. |
   | `run.json` | Filled by the extractor. Wall clock, tool calls, build failures, server rejections, tokens, and cost at the model's rates. The two walk verdicts stay null until section 6. |
   | `code.diff` | The work folder is committed, then diffed against the template baseline. |

9. **Teardown.** The work folder is archived away so the next agent
   cannot find a previous solution, and the device is swept again. For
   gemini, any global memory the agent saved is quarantined into the
   run folder as `global-memory-left-by-agent.md`.

### First gemini run only

Run one probe and eyeball it before trusting gemini metrics

```bash
./runner.sh gemini gemini-3.7-flash cold 99
```

Open the probe's `transcript.jsonl` and check its `run.json` looks
sane. The stream format was verified against gemini-cli v0.57.0, and a
newer CLI could change it. Delete the probe folder and its
`results.csv` row afterward.

## 5. Run manually (interactive session)

For hand-driven runs such as the original two-build experiment.

1. Prepare a fresh scaffold folder, seeded server, and clean device by
   hand, as in the harness steps above.
2. Start the agent in the scaffold folder, paste the prompt verbatim,
   and follow the operator rules in `docs/protocol.md`. Answer product
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

## 6. The human walk (mandatory, per run)

Install the built APK from
`harness/archive/<run_id>/app/build/outputs/apk/debug/` and use the
app. Check four things.

1. The register shows the three patients. For ohs runs this proves
   sync works.
2. A new visit can be recorded.
3. The visit survives a force-stop and relaunch.
4. For ohs runs, the visit reached the server. Check
   `http://localhost:8080/fhir/QuestionnaireResponse?_sort=-_lastUpdated`

Record `verified_working` and `round_trip_pass` in the run's
`run.json`, mirror them into its `results.csv` row, and add a one-line
note for anything interesting. This step exists because two broken apps
passed every automated check.

## 7. When things go wrong

**Usage or quota limit.** The campaign halts itself with a clear
message. Rerun `./campaign.sh <manifest>` after the limit resets and it
continues where it stopped.

**A junk run got collected.** Delete `runs/<id>`,
`harness/archive/<id>`, `harness/logs/<id>.log`, the leftover agent
state for the work path, and the run's `results.csv` row. The campaign
will redo it.

**results.csv looks wrong.** It is derived data. Regenerate it from
the `run.json` files, which are the source of truth.

## 8. Reading the results

`results.csv` has one row per run. `results/grid.md` holds the current
grid and takeaways. Each run's `transcript.md` is the readable record
and `transcript.jsonl` the parseable one.
