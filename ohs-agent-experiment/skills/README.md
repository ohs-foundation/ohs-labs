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
`.claude/skills/<name>/SKILL.md`, and is equally readable pasted into any
other agent's context (Gemini CLI etc.) - part of the retest is checking
they help a non-Claude agent too.

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
