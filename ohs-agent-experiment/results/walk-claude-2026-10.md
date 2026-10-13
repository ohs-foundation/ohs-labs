# Claude current models, app walk

As of 2026-10-13. 24 runs, Claude Code at medium effort, two runs per cell.
Haiku 5.5, Sonnet 5.5, Opus 5.5 and Fable 5.1 across cold, ohs and
ohs-skills. Per run data is in `runs/s1-*-claude-*-medium-*/`.

## At a glance

Average of two runs. Cost is at API rates.

| Model | Cold | OHS | OHS + skills |
|---|---|---|---|
| Haiku 5.5 | works, $0.05, 4.2 min | 1 works, 1 cannot save, $0.15, 5.2 min | works, $0.20, 5.8 min |
| Sonnet 5.5 | works, $0.24, 1.5 min | works, $0.78, 5.8 min | works, $0.52, 3.5 min |
| Opus 5.5 | works, $0.70, 4.0 min | works, $2.65, 7.8 min | works, $1.31, 4.2 min |
| Fable 5.1 | works, $1.53, 3.8 min | works, $7.47, 17.8 min | works, $2.66, 6.0 min |

## How each app was tested

Each app got a fresh HAPI server with the seed data and a clean emulator.
The walk, driven over adb:

1. The register lists the 3 patients.
2. Opening Grace Thompson shows her past visit.
3. The visit form opens.
4. The form is filled in. Weight 73.4, BP 131/86, severe headache, notes "walktest".
5. The form is submitted.
6. The new visit shows on the detail screen.
7. Sync. The new Encounter, Observations and QuestionnaireResponse reach the server.
8. After a restart the new visit is still there.

Cold apps have no server, so step 7 does not apply.

## Results

| Run | Patients | Detail | Form | Fill | Submit | Shows visit | Sync | Restart |
|---|---|---|---|---|---|---|---|---|
| cold-haiku-1 | pass | pass | pass | pass | pass | pass | n/a | pass |
| cold-haiku-2 | pass | pass | pass | pass | pass | pass | n/a | pass |
| cold-sonnet-1 | pass | pass | pass | pass | pass | pass | n/a | pass |
| cold-sonnet-2 | pass | pass | pass | pass | pass | pass | n/a | pass |
| cold-opus-1 | pass | pass | pass | pass | pass | pass | n/a | pass |
| cold-opus-2 | pass | pass | pass | pass | pass | pass | n/a | pass |
| cold-fable-1 | pass | pass | pass | pass | pass | pass | n/a | pass |
| cold-fable-2 | pass | pass | pass | pass | pass | pass | n/a | pass |
| ohs-haiku-1 | pass | pass | pass | pass | pass | partial | pass | pass |
| ohs-haiku-2 | pass | pass | pass | pass | **FAIL** | **FAIL** | **FAIL** | n/a |
| ohs-sonnet-1 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-sonnet-2 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-opus-1 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-opus-2 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-fable-1 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-fable-2 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-skills-haiku-1 | pass | pass | pass | pass | pass | partial | pass | pass |
| ohs-skills-haiku-2 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-skills-sonnet-1 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-skills-sonnet-2 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-skills-opus-1 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-skills-opus-2 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-skills-fable-1 | pass | pass | pass | pass | pass | pass | pass | pass |
| ohs-skills-fable-2 | pass | pass | pass | pass | pass | pass | pass | pass |

21 of 24 apps pass every step.

## Problems found

- **ohs-haiku-2 cannot save a visit.** Every save gets HTTP 422 from the
  server (`HAPI-0330: UUIDs must be valid and lowercase`). The app posts a
  transaction bundle with `urn:uuid:visit-encounter` as a fullUrl. Nothing
  is saved anywhere. The smoke check passed because the app launches.
- **ohs-haiku-1 and ohs-skills-haiku-1 do not refresh after saving.** The
  visit is saved to the server, but the detail screen only shows it after
  going back and opening the patient again.

## How each OHS app stores and syncs

| Model | OHS | OHS + skills |
|---|---|---|
| Haiku | no FHIR engine, writes straight to the server. SDC form in run 2, own form in run 1 | no FHIR engine, writes straight to the server. SDC form |
| Sonnet | no FHIR engine, writes straight to the server. SDC form | FHIR engine and sync. SDC form |
| Opus | FHIR engine and sync. SDC form | FHIR engine and sync. SDC form |
| Fable | FHIR engine and sync. SDC form. Run 2 downloads with the engine and uploads with its own HTTP code | FHIR engine and sync. SDC form |

Apps without the FHIR engine keep no local FHIR store. They pass this walk
because the server was always reachable. They would not work offline,
which this walk did not test.

## Limits

- One patient and one visit per app.
- Offline use and conflict handling were not tested.
- The walk checks behaviour, not code quality.
