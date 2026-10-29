# Offline test and quality checklist

As of 2026-10-23. The 20 OHS and OHS + skills apps from `results.csv`
(Gemini 3.8 Flash, Haiku 5.5, Sonnet 5.5, Opus 5.5, Fable 5.1, two runs
each). Checks 1 to 5 and 8 come from the earlier walks
(`walk-claude-2026-10.md` and the Gemini walk). Checks 6, 7 and 9 come from
this offline test.

## The 9 checks

1. Lists the patients.
2. Shows a patient's past visits.
3. Uses the clinic's visit form (the server's `anc-contact` Questionnaire).
4. Saves a new visit.
5. The visit survives a restart.
6. Saves a visit while offline.
7. The offline visit uploads once back online.
8. The server accepts the data as valid FHIR.
9. The app reopens while offline.

The prompt never asked for offline use. Checks 6, 7 and 9 are our own bar,
because frontline clinics lose signal.

## How the offline test was run

Each app got a fresh HAPI server with the seed data and a clean emulator.

1. Launch online and let the register load.
2. Turn on airplane mode.
3. Open Grace Thompson, record a visit (weight 73.4, BP 131/86) and save.
4. Restart the app, still offline, and check the visit is there.
5. Turn airplane mode off. Check the server after 60s, then after a relaunch,
   then after any Sync or Refresh button.

Server counts use `Cache-Control: no-cache`. HAPI caches search results for
about a minute, and stale counts hide uploads.

Grace's due date (2026-10-15) has passed, so three apps hide her from the
register. Emily Carter was used there.

## Results

| App | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | Score |
|---|---|---|---|---|---|---|---|---|---|---|
| ohs-gemini-1 | pass | pass | pass | pass | pass | pass | FAIL | pass | pass | 8/9 |
| ohs-gemini-2 | pass | pass | pass | pass | pass | pass | FAIL | pass | pass | 8/9 |
| ohs-haiku-1 | pass | pass | FAIL | pass | pass | FAIL | FAIL | pass | FAIL | 5/9 |
| ohs-haiku-2 | pass | pass | pass | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | 3/9 |
| ohs-sonnet-1 | pass | pass | pass | pass | pass | FAIL | FAIL | pass | FAIL | 6/9 |
| ohs-sonnet-2 | pass | pass | pass | pass | pass | FAIL | FAIL | pass | FAIL | 6/9 |
| ohs-opus-1 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-opus-2 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-fable-1 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-fable-2 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-skills-gemini-1 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-skills-gemini-2 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-skills-haiku-1 | pass | pass | pass | pass | pass | FAIL | FAIL | pass | FAIL | 6/9 |
| ohs-skills-haiku-2 | pass | pass | pass | pass | pass | FAIL | FAIL | pass | FAIL | 6/9 |
| ohs-skills-sonnet-1 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-skills-sonnet-2 | pass | pass | pass | pass | pass | pass | pass | pass | FAIL | 8/9 |
| ohs-skills-opus-1 | pass | pass | pass | pass | pass | pass | pass | pass | FAIL | 8/9 |
| ohs-skills-opus-2 | pass | pass | pass | pass | pass | pass | pass | pass | FAIL | 8/9 |
| ohs-skills-fable-1 | pass | pass | pass | pass | pass | pass | pass | pass | FAIL | 8/9 |
| ohs-skills-fable-2 | pass | pass | pass | pass | pass | pass | pass | pass | FAIL | 8/9 |

Average: OHS 7.2/9, OHS + skills 7.9/9. Gemini runs map to the archive as
ohs-medium-2/3 and ohs-skills-medium-6/7.

## Problems found

- **Gemini OHS never uploads offline visits.** Run 1 stores the visit in FHIR
  Engine but uploads with a one-shot HTTP PUT on save. Offline, the PUT fails,
  the error is logged and dropped, and nothing retries. Run 2 keeps a
  SharedPreferences cache and has no upload queue. Neither uploads after 60s,
  a relaunch, or the Refresh button.
- **Haiku (all four) and Sonnet OHS need the server.** Offline, the visit list,
  the form, or both show "Failed to connect", so no visit can be recorded.
- **Five OHS + skills apps crash when reopened offline.** After a failed
  offline sync, launching the app offline throws
  `IllegalStateException: Inconsistent terminal syncJobStatus : Failed` from
  FHIR Engine `Sync.createSyncStateForOneTimeSync` (`Sync.kt:311`). The visit
  is kept on the device and uploads on the next online launch. All five wait
  on the `Sync.oneTimeSync` status flow on launch, the pattern in
  `skills/kotlin-fhir-engine/SKILL.md`. Fable OHS run 1 hit the same error
  during its build and worked around it by watching WorkManager directly.
- **Upload timing differs.** Gemini OHS + skills and Sonnet OHS + skills run 1
  upload within 60s of reconnecting. The other passing apps upload on the next
  launch. Opus OHS also has a Sync button.

## FHIR without OHS (2026-10-24)

The fair baseline: same prompt and FHIR server as ohs, but no OHS libraries
in the project and the agent free to use any library (`build-c-prompt.md`,
`template-src/fhir`). Every app talks to the server live over plain HTTP
(OkHttp or HttpURLConnection) and writes the FHIR JSON by hand. None stores
anything on the device, so none can record a visit offline.

| App | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | Score |
|---|---|---|---|---|---|---|---|---|---|---|
| fhir-gemini-1 | pass | pass | FAIL | pass | pass | FAIL | FAIL | pass | FAIL | 5/9 |
| fhir-gemini-2 | pass | pass | FAIL | pass | pass | FAIL | FAIL | pass | FAIL | 5/9 |
| fhir-haiku-1 | pass | pass | pass | pass | pass | FAIL | FAIL | pass | FAIL | 6/9 |
| fhir-haiku-2 | pass | pass | pass | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | 3/9 |
| fhir-sonnet-1 | pass | pass | pass | pass | pass | FAIL | FAIL | pass | FAIL | 6/9 |
| fhir-sonnet-2 | pass | pass | pass | pass | pass | FAIL | FAIL | pass | FAIL | 6/9 |
| fhir-opus-1 | pass | pass | pass | pass | pass | FAIL | FAIL | pass | FAIL | 6/9 |
| fhir-opus-2 | pass | pass | pass | pass | pass | FAIL | FAIL | pass | FAIL | 6/9 |
| fhir-fable-1 | pass | pass | pass | pass | pass | FAIL | FAIL | pass | FAIL | 6/9 |
| fhir-fable-2 | pass | pass | pass | pass | pass | FAIL | FAIL | pass | FAIL | 6/9 |

Average 5.5/9.

- **Gemini hand-builds the visit form.** Only the danger-sign options are read
  from the Questionnaire, so check 3 fails. The Claude apps render the form
  from the Questionnaire's items.
- **Haiku run 2 cannot save.** The server rejects every visit with HTTP 422
  (HAPI-0330), the same failure as ohs-haiku-2.
- **Several apps show a new visit only after reopening the patient** (Gemini
  1 and 2, Haiku 1, Opus 1, Fable 1 and 2). The visit is on the server. Counted
  as a pass for check 4.
- **Fable run 2 was rerun.** The first attempt hung on a broken heredoc and a
  wait loop that matched itself. It was killed after 19 min and removed.

## OHS + skills rerun with skills v2.5 (2026-10-28)

The kotlin-fhir-engine skill was updated to v2.5 ("Sync without crashes",
see `skills/README.md`) after the offline test above found the crash. The
ohs-skills condition was rerun with the same prompt, templates, models and
effort (`harness/manifest-skills-v25.txt`), then walked with the same 9
checks. Claude models are replicates 8 and 9. Gemini uses replicates 13 and
15: run 8 was discarded (a second emulator broke the harness), runs 10, 11
and 14 were cancelled or interrupted, and runs 9, 12 and 16 were not walked
(9 and 12 were slowed by heavy self-testing and API latency, 16 has no
archived build).

| App | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | Score |
|---|---|---|---|---|---|---|---|---|---|---|
| ohs-skills-gemini-13 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-skills-gemini-15 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-skills-haiku-8 | pass | pass | pass | pass | pass | pass | FAIL | FAIL | FAIL | 6/9 |
| ohs-skills-haiku-9 | pass | pass | pass | pass | pass | pass | FAIL | FAIL | FAIL | 6/9 |
| ohs-skills-sonnet-8 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-skills-sonnet-9 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-skills-opus-8 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-skills-opus-9 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-skills-fable-8 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |
| ohs-skills-fable-9 | pass | pass | pass | pass | pass | pass | pass | pass | pass | 9/9 |

Average 8.4/9 (skills v2.4: 7.9/9).

- **The offline crash is gone.** Every app that uses FHIR Engine reopened
  offline without crashing, showing a status such as "Waiting to sync" or
  "Sync: Enqueued". The crash buffer stayed empty.
- **Offline visits upload by themselves.** In all eight FHIR Engine apps the
  visit saved offline reached the server within 60 seconds of reconnecting,
  without relaunching the app (WorkManager retry). With skills v2.4 most
  apps needed a relaunch.
- **Haiku still never uses FHIR Engine.** Both apps send visits straight to
  the server over HTTP, so they cannot load or save anything offline.
- **Sonnet's apps do not upload the QuestionnaireResponse.** The Encounter
  and Observations reach the server, which is all the checks require.
- **Walk notes.** Fable 9 and Gemini 15 needed the offline visit entered a
  second time by hand because the automated input missed; both apps then
  passed. Haiku 9 and some others show a new visit only after reopening the
  patient; counted as a pass for check 4, as before.

Cost and time per build, average of the two walked runs, at API prices:

| Model | Skills v2.4 | Skills v2.5 |
|---|---|---|
| Gemini 3.8 Flash | $1.46, 6.5 min | $1.29, 15.2 min |
| Claude Fable 5.1 | $2.66, 6.1 min | $2.73, 5.2 min |
| Claude Opus 5.5 | $1.31, 4.3 min | $1.17, 4.7 min |
| Claude Sonnet 5.5 | $0.52, 3.5 min | $0.54, 3.2 min |
| Claude Haiku 5.5 | $0.20, 5.8 min | $0.22, 5.7 min |

The blog uses Gemini run 15 alone for OHS + skills ($1.22, 13.5 min). Cost barely changed. Gemini's time is not comparable: its steps took about
twice as long per action (8 to 9 s, against about 4 s before) while the
amount of work stayed the same, which points to slower API responses on the
day of the rerun.

## Stricter sync checks: strict upload check and check 10 (2026-10-28)

Several apps without skills passed the upload check (check 7 in this file, check 8 in the blog) only because the test reopened
them, which triggered their sync. Two stricter checks separate sync that
keeps working on its own from sync that only runs while the app is open.

- **Strict upload check, "uploads by itself".** The offline visit reaches the
  server once the network is back, without reopening the app or tapping
  anything. Re-scored from the offline test above, no new runs.
- **Check 10, "uploads even if the app is closed".** Fresh server and
  install, open online, airplane mode on, save a visit, press Home and
  `am kill` the app (ends the process but keeps scheduled WorkManager work,
  unlike force-stop), network back within 30 s, never reopen the app, watch
  the server for 5 minutes. The script first confirms the save went through
  (form closed) so a missed tap cannot show up as a fail.

Check 10 was run on the 12 apps that can save offline. Every other app
already fails the offline save check, so it fails both stricter checks too.

| App | Strict upload | Check 10 | How it syncs |
|---|---|---|---|
| ohs-skills-gemini-13 (v2.5) | pass | pass, within 30 s | WorkManager retry (`FhirSyncWorker`) |
| ohs-skills-gemini-15 (v2.5) | pass | pass, within 30 s | same |
| ohs-skills-sonnet-8 (v2.5) | pass | pass, within 30 s | same |
| ohs-skills-sonnet-9 (v2.5) | pass | pass, within 30 s | same |
| ohs-skills-opus-8 (v2.5) | pass | pass, within 30 s | same |
| ohs-skills-opus-9 (v2.5) | pass | pass, within 30 s | same |
| ohs-skills-fable-8 (v2.5) | pass | pass, within 30 s | same |
| ohs-skills-fable-9 (v2.5) | pass | pass, within 30 s | same |
| ohs-opus-1 | FAIL | FAIL | `runSync` inside the app process, no scheduled work |
| ohs-opus-2 | FAIL | FAIL | `runSync` tied to the screen |
| ohs-fable-1 | FAIL | FAIL | sync worker enqueued with no retries, failed at once offline |
| ohs-fable-2 | FAIL | FAIL | own HTTP PUT that runs only while the app is open |

In check 10 every v2.5 app showed a sync job that failed offline with
`RETRY`, then WorkManager restarted the app process in the background and
uploaded the visit. The four apps without skills scheduled no retryable
work, so nothing ran until the app was opened again.

Test notes: the first check 10 attempt on ohs-skills-opus-8 was invalid
(the save never happened) and was redone with the save confirmed. One
attempt on ohs-fable-1 froze the app with an ANR during the scripted typing
and was redone with gentler input.

### Scores out of 10 (strict upload check plus check 10)

| Model | OHS (libraries only) | OHS + Skills, v2.5 |
|---|---|---|
| Gemini 3.8 Flash | 8 | 10 |
| Claude Fable 5.1 | 8 | 10 |
| Claude Opus 5.5 | 8 | 10 |
| Claude Sonnet 5.5 | 6 | 10 |
| Claude Haiku 5.5 | 4 | 6 |
| **Average** | 6.8 | 9.2 |

With the stricter checks no app built without skills is fully working, and
every v2.5 skills app except Haiku's is.

## Limits

- One visit per app, one offline period.
- Cold apps were not tested offline. They never use the network.
- Conflicts and duplicate handling were not tested.
