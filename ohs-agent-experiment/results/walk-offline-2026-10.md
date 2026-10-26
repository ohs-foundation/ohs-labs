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

## Limits

- One visit per app, one offline period.
- Cold apps were not tested offline. They never use the network.
- Conflicts and duplicate handling were not tested.
