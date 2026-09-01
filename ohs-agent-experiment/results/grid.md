# Sweep 1 Results — build scenario, one run per cell

As of 2026-08-26. All runs below used the Claude Code agent harness
(`run.json.harness` records this per run; Gemini rows would appear in
the same table when run). Status is from the on-emulator walk (launch + register
showing data; full visit-recording walk still pending for the non-fable
cells). Cost is at each model's API rates; tokens are output tokens
(cache traffic excluded — see runs/<id>/run.json for full token detail).

## At a glance

| Model | Scratch               | OHS | OHS + skills |
|---|-----------------------|---|---|
| Fable 5 | works, $13.00, 29 min | works, $61.00, 33 min | works, $14.31, 10 min |
| Opus 5 | works, $8.20, 14 min  | works, $28.26, 43 min | works, $11.39, 14 min |
| Sonnet 5 | works, $2.51, 9 min   | works, $18.96, 37 min | works, $25.97, 58 min |
| Haiku 4.5 | works, $1.27, 9 min   | BROKEN (crash), $0.98, 16 min | BROKEN (no sync), $1.92, 12 min |

(Cold Fable also has replicate 2: works, $10.22, 9 min.)

## Full detail per run

| Run | Status | Cost | Minutes | Output tokens |
|---|---|---|---|---|
| cold-fable-01 | works | $13.00 | 29 | 90,089 |
| cold-fable-02 | works | $10.22 | 9 | 87,048 |
| cold-opus-01 | works | $8.20 | 14 | 114,332 |
| cold-sonnet-01 | works | $2.51 | 9 | 58,874 |
| cold-haiku-01 | works | $1.27 | 9 | 55,954 |
| ohs-fable-01 | works | $61.00 | 33 | 250,660 |
| ohs-opus-01 | works | $28.26 | 43 | 162,162 |
| ohs-sonnet-01 | works | $18.96 | 37 | 253,981 |
| ohs-haiku-01 | BROKEN: crashes at launch | $0.98 | 16 | 51,354 |
| ohs-skills-fable-01 | works | $14.31 | 10 | 128,378 |
| ohs-skills-opus-01 | works | $11.39 | 14 | 106,201 |
| ohs-skills-sonnet-01 | works | $25.97 | 58 | 324,916 |
| ohs-skills-haiku-01 | BROKEN: register stays empty | $1.92 | 12 | 95,670 |

## What the grid says so far (n=1 per cell — treat as signal, not proof)

- **Every cold build works.** All three models can invent their own private
  stack. The cold column is the easy column.
- **The OHS stack works for Fable and Sonnet** — with or without skills —
  including live sync from the HAPI server (the harder feat).
- **Haiku is the boundary case.** Without skills it refused to engage the
  unfamiliar SDK (went Room, crashed). With skills it adopted the correct
  architecture but dropped one wire (sync never called). Skills moved it
  from "wrong stack + crash" to "right stack, one missing call" — a real
  gradient, not yet a working app.
- **Skills cut Fable's OHS cost ~75%** ($61 to $14.31) at equal quality —
  the predicted skills effect, on its first test.
- **Opus repeats the skills effect** ($28.26/43min to $11.39/14min, both
  working) — and OHS+skills+Opus is now the cheapest reliable way to
  build on OHS: $11.39, under Fable+skills' $14.31.
- **Skills made Sonnet slower and costlier** ($18.96/37min to $25.97/58min,
  both working). Whether that bought quality (more verification, better
  code) needs the full walk and replicates.
- **Both failures passed the smoke check** (launch-without-crash). Only
  the human walk caught them — the walk stays in the protocol.

## Failure detail

| Run | Failure mode | Root cause |
|---|---|---|
| s1-ohs-haiku-01 | `FATAL EXCEPTION` at launch | Declared the OHS deps but wrote zero code against them; added Room 2.6.1 with `annotationProcessor` instead of KSP, so `AncDatabase_Impl` is never generated — compiles clean, dies at runtime |
| s1-ohs-skills-haiku-01 | App runs, register permanently empty | `FhirRepository.syncData()` implemented (correctly, per the skills) but no call site anywhere — download never happens; local database stays empty |

Full per-run data: `results.csv` and `runs/<run_id>/run.json`.
