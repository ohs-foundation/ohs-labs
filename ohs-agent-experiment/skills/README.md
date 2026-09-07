# OHS library skills

Agent-facing documentation for the three OHS libraries, distilled from the
build B experiment (2026-08-24): everything in these files is either lifted
from that run's verified working code or a gotcha that run discovered the
hard way. Nothing is recalled from training data.

- `kotlin-fhir/SKILL.md` - dev.ohs.fhir:fhir-model (R4 model classes)
- `kotlin-fhir-engine/SKILL.md` - dev.ohs.fhir:fhir-engine (local store + sync)
- `kotlin-fhir-data-capture/SKILL.md` - dev.ohs.fhir:fhir-data-capture (Questionnaire forms)

## Authoring discipline (keep it this way)

These document the **libraries, not any app**. No task recipes, no
app-specific field names, no "build a register screen" instructions. That is
what keeps the skills-condition retest honest (the agent must still design
the app) and what makes these shippable with the toolkit afterward.

Plain markdown with skill frontmatter: drops into a Claude Code project as
`.claude/skills/<name>/SKILL.md`, and for Gemini the same three files are
packaged (frontmatter stripped, concatenated) as a single `GEMINI.md` by
`harness/setup-templates.sh` into the `ohs-skills-gemini` template - part
of the retest is checking they help a non-Claude agent too.

## Using in the retest (skills condition)

1. Fresh scaffold from the build B baseline.
2. Copy the three skill folders into the scaffold's `.claude/skills/`.
3. Same build prompt, same rules as every other run.
4. Predicted effect (on record in `../docs/protocol.md` Part B): build cost drops
   from ~$60 toward ~$13 (the difference was mostly SDK archaeology),
   fewer self-correction loops, no repeat of the three known gotchas
   (upload strategy, DataCapture init, JVM 21).

## Gotchas encoded (source: build B run)

- fhir-engine 2.0.0-alpha02 transaction-bundle upload rejected by strict
  servers (fullUrl); use `UploadStrategy.forIndividualRequest`.
- `DataCapture.initialize()` required before first form render (crash).
- Artifacts target JVM 21; consumers must bump `jvmTarget`.
- `work-runtime-ktx` and `kotlinx-serialization-json` needed at compile scope.
- `TimestampContext` method name is `getLasUpdateTimestamp` (as published).
- FHIR `String` collides with Kotlin's; alias the import.

## Versions

The skills are part of the experimental treatment, so changes are
versioned here and runs are only comparable within a version.

- **v1** (2026-08-25). Initial three skills, distilled from the first
  verified OHS build. Used by every ohs-skills run through sweep 1.
- **v2** (2026-09-07). kotlin-fhir-engine skill substantially expanded
  after repeated sync failures in eval runs: sync must be triggered
  explicitly, every synced type must be listed for download, upload
  strategy reasoning (PUT-as-create vs POST, squash, the bundle 422),
  watermark semantics and the stale-watermark trap, retry and
  re-enqueue behavior, terminal-state collection of the status flow,
  cleartext config, and a symptom-to-fix troubleshooting table. All
  API claims in the engine skill were then verified against the engine
  source at tag v2.0.0-alpha02 (upload factories and their
  NotImplementedError guards, the misspelled `getLasUpdateTimestamp`,
  the `existingWorkPolicy`-must-be-named signature, CurrentSyncJobStatus
  subclasses, and the FhirEngine CRUD signatures). ohs-skills runs from
  this date use v2 and should not be pooled with v1 runs when comparing
  cells.
