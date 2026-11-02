# OHS library skills

Agent-facing documentation for the three OHS libraries, used in the
`ohs-skills` condition. It grew from the failures seen in earlier
runs. API claims
are checked against the library source, never recalled from training
data. Current version v2.5, history in [CHANGELOG.md](CHANGELOG.md).

- `kotlin-fhir/SKILL.md` - dev.ohs.fhir:fhir-model (R4 model classes)
- `kotlin-fhir-engine/SKILL.md` - dev.ohs.fhir:fhir-engine (local store + sync)
- `kotlin-fhir-data-capture/SKILL.md` - dev.ohs.fhir:fhir-data-capture (Questionnaire forms)

## Authoring discipline (keep it this way)

These document the **libraries, not any app**. No task recipes, no
app-specific field names, no "build a register screen" instructions. That is
what keeps the `ohs-skills` condition honest (the agent must still design
the app) and what makes these shippable with the toolkit afterward.

Plain markdown with skill frontmatter: drops into a Claude Code project as
`.claude/skills/<name>/SKILL.md`, into an Antigravity CLI project unchanged
as `.agents/skills/<name>/SKILL.md` (the `ohs-skills-antigravity` template),
and for Gemini CLI the same three files are packaged (frontmatter stripped,
concatenated) as a single `GEMINI.md` by `harness/setup-templates.sh` into
the `ohs-skills-gemini` template, so the same skills can be tested on a
non-Claude agent.

## Using them in a run

1. `harness/setup-templates.sh` builds the per-agent skills templates
   from this folder, and `harness/refresh-skills-templates.sh` rebuilds them
   after an edit.
2. Same build prompt, same rules as every other run.
3. After any edit, add a version to `CHANGELOG.md` and do not pool
   the new `ohs-skills` runs with older ones.

How the skills did is in `../README.md` (Results).

## Main gotchas covered

- fhir-engine 2.0.0-alpha02 transaction-bundle upload rejected by strict
  servers (fullUrl). Use `UploadStrategy.forIndividualRequest`.
- `DataCapture.initialize()` required before first form render (crash).
- fhir-engine targets JVM 21, so consumers must bump `jvmTarget` (see v2.4 in the changelog).
- `work-runtime-ktx` and `kotlinx-serialization-json` needed at compile scope.
- `TimestampContext` method name is `getLasUpdateTimestamp` (as published).
- FHIR `String` collides with Kotlin's, so alias the import.
