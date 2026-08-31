---
name: kotlin-fhir-data-capture
description: Rendering FHIR Questionnaires as Compose forms with dev.ohs.fhir:fhir-data-capture and collecting QuestionnaireResponse answers. Use when an app needs a data-entry form defined by a FHIR Questionnaire.
---

# kotlin-fhir-data-capture (dev.ohs.fhir:fhir-data-capture)

Renders a FHIR `Questionnaire` as a complete Jetpack Compose form - date
pickers, numeric fields, single/multi-select choices, text - and returns the
filled `QuestionnaireResponse`. The form definition is data, not code: to
change the form, change the Questionnaire resource.

```kotlin
implementation("dev.ohs.fhir:fhir-data-capture:2.0.0-alpha02")   // Maven Central
```

Artifacts are compiled for JVM 21: set the app module's `jvmTarget` to 21.

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

Skipping this is a runtime crash on first render, not a compile error.

## The Compose entry point

`dev.ohs.fhir.datacapture.Questionnaire` is a composable taking the
Questionnaire as a JSON string:

```kotlin
import dev.ohs.fhir.datacapture.Questionnaire

Questionnaire(
  questionnaireJson = json,                 // Questionnaire resource as JSON text
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

Notes on the contract, all load-bearing:

- `onSubmit` hands you a getter, not the response itself. Call
  `getResponse()` (suspending) to run validation and obtain the
  `QuestionnaireResponse`.
- When validation fails, `getResponse()` throws `CancellationException`
  and the form displays the per-question errors itself. Catch it and do
  nothing.
- The JSON string typically comes from serializing a `fhir-model`
  `Questionnaire` (see the kotlin-fhir skill) - for example one fetched
  from a server and stored in the FHIR engine.

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
validation on submit.
