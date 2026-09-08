---
name: kotlin-fhir-data-capture
description: Rendering FHIR Questionnaires as Compose forms with dev.ohs.fhir:fhir-data-capture, collecting and validating a QuestionnaireResponse, prefilling/editing, configuring the form, extracting resources, and avoiding the stale-form-state trap. Use when an app needs a data-entry form defined by a FHIR Questionnaire. All API is verified against the engine source at the published 2.0.0-alpha02 commit.
---

# kotlin-fhir-data-capture (dev.ohs.fhir:fhir-data-capture)

Renders a FHIR `Questionnaire` as a complete Jetpack Compose form - date
pickers, numeric fields, single/multi-select choices, text - and returns the
filled `QuestionnaireResponse`. The form definition is data, not code: to
change the form, change the Questionnaire resource.

```kotlin
implementation("dev.ohs.fhir:fhir-data-capture:2.0.0-alpha02")   // Maven Central
```

The data-capture Android artifact targets JVM 11, so it needs at least `jvmTarget = 11`. In the full OHS stack you set `jvmTarget = 21` because the FHIR engine requires it (see the engine skill).

> Version note: at 2.0.0-alpha02 the library is initialized with
> `DataCapture.initialize(context)` (below). A later refactor (alpha03+)
> replaces that singleton with a `LocalDataCaptureConfig` CompositionLocal.
> This file documents alpha02. If you are on a newer version and
> `DataCapture` is unresolved, provide `DataCaptureConfig` via
> `LocalDataCaptureConfig` instead.

## Initialize before first use (or the form crashes)

Once, in `Application.onCreate`, before any form is shown:

```kotlin
import dev.ohs.fhir.datacapture.DataCapture

class MyApplication : Application() {
  override fun onCreate() {
    super.onCreate()
    DataCapture.initialize(this)
  }
}
```

This is not optional. Internally the form calls `DataCapture.getConfiguration()`,
which throws if init was skipped, with the message "DataCapture not
initialized. Initialize the library with DataCapture.initialize(context)".
It is a runtime crash on first render, not a compile error.

To supply custom questionnaire components or behavior, have the
`Application` implement `DataCaptureConfig.Provider`; `initialize` reads the
config from it:

```kotlin
class MyApplication : Application(), DataCaptureConfig.Provider {
  override fun getDataCaptureConfig() = DataCaptureConfig(/* custom parsers, etc. */)
}
```

## The Compose entry point

The full signature (only `onSubmit` and `onCancel` are required):

```kotlin
@Composable
fun Questionnaire(
  questionnaireJson: String,                         // the Questionnaire resource as JSON
  questionnaireResponseJson: String? = null,         // prefill / edit an existing response
  questionnaireLaunchContextMap: Map<String, String>? = null,
  config: QuestionnaireConfig = QuestionnaireConfig(),
  matchersProvider: QuestionnaireItemViewFactoryMatchersProvider? = null,
  onSubmit: (suspend () -> QuestionnaireResponse) -> Unit,
  onCancel: () -> Unit,
)
```

Typical use:

```kotlin
import dev.ohs.fhir.datacapture.Questionnaire

Questionnaire(
  questionnaireJson = json,
  onSubmit = { getResponse ->
    scope.launch {
      try {
        val response: QuestionnaireResponse = getResponse()
        // persist / process the response
      } catch (e: CancellationException) {
        // answer validation failed; the form is already showing the errors -
        // swallow this and let the user correct the answers
      }
    }
  },
  onCancel = { /* user backed out */ },
)
```

Notes on the contract, all load-bearing and source-verified:

- `onSubmit` hands you a getter, not the response itself. Call
  `getResponse()` (suspending) to run validation and obtain the
  `QuestionnaireResponse`.
- When validation fails, `getResponse()` throws `CancellationException`
  and the form displays the per-question errors itself. Catch it and do
  nothing. (If `config.showSubmitAnywayWhenValidationFails` is true, the
  form also offers a "submit anyway" path that returns the response
  without re-validating.)
- The JSON string typically comes from serializing a `fhir-model`
  `Questionnaire` (see the kotlin-fhir skill) - for example one fetched
  from a server and stored in the FHIR engine.

### Configuring the form

`QuestionnaireConfig` (all fields with their defaults):

```kotlin
data class QuestionnaireConfig(
  val showSubmitButton: Boolean = true,
  val showCancelButton: Boolean = true,
  val showReviewPage: Boolean = false,
  val showReviewPageFirst: Boolean = false,
  val isReadOnly: Boolean = false,              // render answers, disallow editing
  val showAsterisk: Boolean = false,
  val showRequiredText: Boolean = true,
  val showOptionalText: Boolean = false,
  val showNavigationLongScroll: Boolean = false,
  val submitButtonText: String? = null,
  val showSubmitAnywayWhenValidationFails: Boolean = true,
)
```

### Prefilling or editing an existing response

Pass a serialized `QuestionnaireResponse` as `questionnaireResponseJson`
to open the form populated with previous answers (viewing or editing a
saved visit). Combine with `config = QuestionnaireConfig(isReadOnly = true)`
for a read-only view.

## The stale-form trap (blank form shows the previous answers)

Symptom: after submitting a form and opening it again for a new record,
the fields still hold the previous entry. Killing and reopening the app
clears them. This is the most common integration bug with this library.

Cause, verified in the source: the composable caches its view-model with

```kotlin
val viewModel = viewModel(key = questionnaireJson) { QuestionnaireViewModel(...) }
```

`viewModel(key = ...)` (androidx compose) stores the instance in the
current `ViewModelStoreOwner`, keyed only by the questionnaire JSON. Every
new record of the same form uses the identical JSON, so the same
view-model - with the previously typed answers still in it - is returned
for as long as that store owner lives. An app restart destroys the owner,
which is why restarting "fixes" it. Note the key ignores
`questionnaireResponseJson`, so passing a different response does not force
a fresh view-model either.

Fix: host `Questionnaire` in a `ViewModelStoreOwner` scoped to one form
session, so opening the form again is a new owner with a fresh view-model.

- With Compose Navigation (recommended): give the form its own
  destination and `popBackStack()` when it closes, on both submit and
  cancel. Navigating to it again creates a new `NavBackStackEntry` (a new
  store owner), so the form starts blank.

  ```kotlin
  composable("newVisit/{patientId}") { /* ... */
    Questionnaire(
      questionnaireJson = json,
      onSubmit = { getResponse -> scope.launch { save(getResponse()); navController.popBackStack() } },
      onCancel = { navController.popBackStack() },
    )
  }
  ```

- Do NOT show the form by toggling a boolean inside a long-lived screen or
  the Activity. There the store owner is the Activity, which lives for the
  whole process, so the same view-model (and its old answers) is reused
  until the app restarts - exactly the reported symptom.

## Reading answers from the response

Answers sit in a tree of items keyed by `linkId`, possibly nested (groups)
- flatten first, then read each answer with the choice-type accessors:

```kotlin
val answers = mutableMapOf<String, MutableList<QuestionnaireResponse.Item.Answer>>()
fun collect(items: List<QuestionnaireResponse.Item>) {
  items.forEach { item ->
    item.linkId.value?.let { answers.getOrPut(it) { mutableListOf() }.addAll(item.answer) }
    collect(item.item)                          // nested groups
    item.answer.forEach { collect(it.item) }    // answers can nest items too
  }
}
collect(response.item)

val date    = answers["visit-date"]?.firstOrNull()?.value?.asDate()?.value?.value
val number  = answers["weight"]?.firstOrNull()?.value?.asDecimal()?.value?.value
val integer = answers["count"]?.firstOrNull()?.value?.asInteger()?.value?.value
val text    = answers["notes"]?.firstOrNull()?.value?.asString()?.value?.value
val choices = answers["symptoms"].orEmpty().mapNotNull { it.value?.asCoding()?.value }
```

A repeating choice question produces one answer per selection - read them
as a list, as in the last line.

## Turning the response into resources

There are two ways to get FHIR resources out of a filled response.

1. **Template-based extraction (built in).** `TemplateExtractionEngine` is
   a public object:

   ```kotlin
   import dev.ohs.fhir.datacapture.extraction.template.TemplateExtractionEngine
   val bundle: Bundle = TemplateExtractionEngine.extract(questionnaire, response)
   ```

   It works only when the Questionnaire declares template extraction
   (the `sdc-questionnaire-templateExtractBundle` /
   `sdc-questionnaire-templateExtract` extensions or item-level template
   declarations). Called on a plain Questionnaire with no templates it
   throws `IllegalArgumentException`. So this pays off only if you author
   the Questionnaire with extraction templates.

2. **Map it yourself.** If the Questionnaire carries no extraction
   templates, read the answers as above and build the `Encounter` /
   `Observation` / etc. resources in code (see the kotlin-fhir skill).
   This is the pragmatic path for a form that was not authored for
   template extraction.

## Completing the response before saving

The rendered response usually needs identity and status fields filled in
before persisting; use the builder (resources are immutable):

```kotlin
val completed = response.toBuilder().apply {
  id = UUID.randomUUID().toString()
  status = Enumeration(value = QuestionnaireResponse.QuestionnaireResponseStatus.Completed)
  subject = subjectReference.toBuilder()
  questionnaire = Canonical(value = questionnaireUrl).toBuilder()
}.build()
```

## What the questionnaire item types render as

| Questionnaire item type | Rendered control |
|---|---|
| `date` | date picker |
| `integer` / `decimal` | numeric keyboard field |
| `choice` | single-select options |
| `choice` with `repeats: true` | multi-select options |
| `text` | multi-line text field |
| `group` | section grouping its child items |

Required items (`"required": true`) are enforced by the form's own
validation on submit; the error surfaces as the `CancellationException`
from `getResponse()` described above.
