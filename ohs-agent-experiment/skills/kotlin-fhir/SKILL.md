---
name: kotlin-fhir
description: Working with dev.ohs.fhir:fhir-model FHIR R4 model classes in Kotlin - constructing resources, reading nested values, choice types, serialization. Use when creating, reading, or serializing FHIR resources (Patient, Observation, Encounter, Questionnaire, etc.).
---

# kotlin-fhir (dev.ohs.fhir:fhir-model)

FHIR R4/R4B/R5 model classes generated from the official StructureDefinitions.
Kotlin Multiplatform; on Android it is a regular dependency.

```kotlin
implementation("dev.ohs.fhir:fhir-model:1.0.0-beta05")   // Maven Central
```

Artifacts are compiled for JVM 21: set the app module's `jvmTarget` to 21.

## Core rules

1. **Resources are immutable data classes** constructed with named arguments.
   R4 classes live in `dev.ohs.fhir.model.r4`.
2. **Every FHIR primitive is a wrapper class**, not a Kotlin primitive:
   `FhirString`, `Code`, `Uri`, `Canonical`, `DateTime`, `Decimal`,
   `Boolean`, `Integer`. You always write `FhirString(value = "...")`, never
   a bare string. The FHIR string type is named `String`, which collides
   with Kotlin's - alias it on import:

   ```kotlin
   import dev.ohs.fhir.model.r4.String as FhirString
   ```
3. **Reading values means unwrapping layer by layer.** Each wrapper exposes
   `.value`. A quantity's number is three levels deep:

   ```kotlin
   // Quantity.value is Decimal; Decimal.value is BigDecimal
   val number = observation.value?.asQuantity()?.value?.value?.value?.toPlainString()
   val id: String? = patient.id            // resource id is a plain String?
   val family = patient.name.firstOrNull()?.family?.value
   ```
4. **Coded fields use `Enumeration`** wrapping a generated enum:

   ```kotlin
   status = Enumeration(value = Observation.ObservationStatus.Final)
   status = Enumeration(value = Encounter.EncounterStatus.Finished)
   ```
5. **Decimals are ionspin BigDecimal** (`com.ionspin.kotlin.bignum.decimal.BigDecimal`),
   available transitively:

   ```kotlin
   Decimal(value = BigDecimal.fromInt(120))
   Decimal(value = BigDecimal.parseString("68.5"))
   ```
6. **Kotlin keywords used as field names are escaped with backticks**,
   e.g. `Encounter(`class` = Coding(...))`.

## Choice types (value[x], effective[x], ...)

Choice elements are nested classes named after the field, with one variant
per allowed type. Construct the variant; read with `asX()` accessors that
return null when the variant differs.

```kotlin
// construct
value = Observation.Value.Quantity(Quantity(...))
value = Observation.Value.CodeableConcept(CodeableConcept(...))
value = Observation.Value.String(FhirString(value = "free text"))
effective = Observation.Effective.DateTime(DateTime(value = FhirDateTime.fromString("2026-01-15")))

// read
observation.value?.asQuantity()      // Observation.Value.Quantity or null
observation.value?.asCodeableConcept()
answer.value?.asDate()?.value?.value // unwrap to the date value
answer.value?.asInteger()?.value?.value
answer.value?.asCoding()?.value
```

## Building common structures

```kotlin
val patientRef = Reference(reference = FhirString(value = "Patient/$patientId"))

val concept = CodeableConcept(
  coding = listOf(
    Coding(
      system = Uri(value = "http://loinc.org"),
      code = Code(value = "29463-7"),
      display = FhirString(value = "Body weight"),
    )
  ),
  text = FhirString(value = "Body weight"),
)

val quantity = Quantity(
  value = Decimal(value = BigDecimal.parseString("68.5")),
  unit = FhirString(value = "kg"),
  system = Uri(value = "http://unitsofmeasure.org"),
  code = Code(value = "kg"),
)

// components (e.g. blood pressure panel) nest the same way
Observation.Component(
  code = concept,
  value = Observation.Component.Value.Quantity(quantity),
)
```

Dates and datetimes parse from ISO strings:

```kotlin
DateTime(value = FhirDateTime.fromString("2026-01-15"))
DateTime(value = FhirDateTime.fromString("2026-01-15T10:30:00+07:00"))
```

## Modifying an existing resource: toBuilder

Instances are immutable; use the builder to change fields. Builder fields
that hold complex types take builders themselves:

```kotlin
val updated = response.toBuilder().apply {
  id = "new-id"                                  // plain values assign directly
  subject = patientRef.toBuilder()               // complex values need .toBuilder()
  status = Enumeration(value = QuestionnaireResponse.QuestionnaireResponseStatus.Completed)
}.build()
```

## JSON serialization

kotlinx-serialization, not a custom parser. Add
`org.jetbrains.kotlinx:kotlinx-serialization-json` as a compile dependency.
The `resourceType` property is emitted automatically.

```kotlin
private val json = Json {
  explicitNulls = false     // otherwise every absent field serializes as null
  encodeDefaults = false
}

val text: String = json.encodeToString(questionnaire)
val res: Patient = json.decodeFromString(text)
```

## Enums for resource types

`ResourceType` lives in `dev.ohs.fhir.model.r4.terminologies`:

```kotlin
import dev.ohs.fhir.model.r4.terminologies.ResourceType
ResourceType.Patient; ResourceType.Observation; ResourceType.Questionnaire
```
