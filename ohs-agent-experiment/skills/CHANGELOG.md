# Skills changelog

The skills are part of the experimental treatment, so changes are
versioned here and runs are only comparable within a version. The
current version is v2.5.

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

- **v2.2** (2026-09-08). kotlin-fhir-data-capture skill expanded and
  source-verified against the *published* 2.0.0-alpha02 commit (the
  version bump commit, not the last commit in the alpha02 window - a
  later refactor within that window replaced the DataCapture singleton
  with LocalDataCaptureConfig, which ships in alpha03. Verifying against
  the wrong commit would have wrongly deleted the correct
  DataCapture.initialize guidance). Adds: the full Questionnaire
  composable signature (questionnaireResponseJson prefill/edit, launch
  context, QuestionnaireConfig, matchers), QuestionnaireConfig fields,
  the DataCaptureConfig.Provider mechanism, TemplateExtractionEngine
  (built-in extraction, requires template extensions or it throws), and
  a prominent write-up of the stale-form-state trap (the form reuses its
  view-model keyed by questionnaire JSON in the current
  ViewModelStoreOwner, so a reopened form shows the previous answers
  until the owner is destroyed. Fix by scoping the form to a popped nav
  destination). Confirmed correct and kept: DataCapture.initialize is
  the right init for alpha02, and its exact not-initialized error.

- **v2.3** (2026-09-08). kotlin-fhir (model) skill: added a verified
  value[x] unwrap example after diagnosing a real run failure. A Gemini
  ohs-skills build showed every estimated due date as "N/A" because it
  stringified the DateTime *element* (asDateTime()?.value?.toString())
  instead of unwrapping to the primitive (asDateTime()?.value?.value).
  Everything upstream (sync, the token search on code, subject linking,
  the stored valueDateTime) was verified correct against the on-device
  DB and the beta05 model source. The bug was purely the choice-type
  unwrap depth. The skill now spells out the two-hop rule (variant ->
  element -> primitive) and the silent-null failure of stopping early.

- **v2.4** (2026-09-08). kotlin-fhir (model) skill expanded and
  adversarially verified against v1.0.0-beta05: completed the primitive
  wrapper list, added a "reading common fields" section (human name,
  reference target id, birthDate, coding code - all using the unwrap
  rule), and noted FhirDateTime is a sealed type with partial-date
  variants. Verification also corrected a jvmTarget claim that was wrong
  in all three skills: the model Android artifact targets JVM 1.8 and
  data-capture targets JVM 11 - neither needs jvmTarget 21. The FHIR
  *engine* (JDK 21 toolchain) is what actually requires the app to set
  jvmTarget 21, so all three skills now state their own target and point
  at the engine as the driver. Also softened an over-broad claim that
  every unqualified String field is the FHIR String (a resource id is
  kotlin.String).
- **v2.5** (2026-10-27). kotlin-fhir-engine skill: sync without crashes.
  The offline test found that `Sync.oneTimeSync`'s status flow throws
  `IllegalStateException: Inconsistent terminal syncJobStatus` after a
  failed offline sync, and five ohs-skills apps that collected it
  unguarded on launch crashed when reopened offline. Added a "Sync
  without crashes" section (`.catch` on every status flow, stop at the
  final state, keep default retry and `KEEP`, no `APPEND` or
  `APPEND_OR_REPLACE`, `Enqueued` means waiting to retry), replaced the
  one-time sync example with a `SyncViewModel`, call `getInstance` right
  after `init`, added a `runSync` section for Desktop and iOS, and new
  troubleshooting rows. ohs-skills runs from this date use v2.5 and
  should not be pooled with earlier runs.
