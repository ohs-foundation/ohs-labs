---
name: kotlin-fhir-engine
description: Using dev.ohs.fhir:fhir-engine on Android - local FHIR database (create, get, search) and bidirectional sync with a FHIR server via WorkManager. Use when storing FHIR resources on-device, querying them, or syncing with a server.
---

# kotlin-fhir-engine (dev.ohs.fhir:fhir-engine)

Offline-first FHIR store for Android with server sync. The local database is
the working store; a FHIR server (e.g. HAPI) is the source of truth. Uses the
`dev.ohs.fhir:fhir-model` classes throughout.

```kotlin
implementation("dev.ohs.fhir:fhir-engine:2.0.0-alpha02")   // Maven Central
// Needed at compile scope (present at runtime transitively, but not compile):
implementation("androidx.work:work-runtime-ktx:2.8.1")
implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.9.0")
```

Artifacts are compiled for JVM 21: set the app module's `jvmTarget` to 21.

## Initialization (once, in Application.onCreate)

```kotlin
import dev.ohs.fhir.engine.FhirEngineConfiguration
import dev.ohs.fhir.engine.FhirEngineProvider
import dev.ohs.fhir.engine.ServerConfiguration

class MyApplication : Application() {
  override fun onCreate() {
    super.onCreate()
    FhirEngineProvider.init(
      FhirEngineConfiguration(
        serverConfiguration = ServerConfiguration(baseUrl = "https://server.example/fhir/"),
      ),
      this,
    )
  }
}
```

Keep the trailing slash on `baseUrl`. Plain-HTTP servers (dev setups) also
need Android cleartext-traffic config in the manifest.

Get the engine anywhere with:

```kotlin
val engine = FhirEngineProvider.getInstance(context.applicationContext)
```

## Local CRUD

```kotlin
import dev.ohs.fhir.engine.get

// create takes a vararg; assign ids yourself (UUIDs) so references
// between resources are stable before and after upload
val encounter = Encounter(id = UUID.randomUUID().toString(), ...)
engine.create(encounter, observation1, observation2)

val patient: Patient = engine.get<Patient>("patient-id")   // throws if absent
```

## Search

`engine.search<T>(Search(resourceType))` returns a list of results; each
result's `.resource` is the model object.

```kotlin
import dev.ohs.fhir.engine.search.ReferenceClientParam
import dev.ohs.fhir.engine.search.Search
import dev.ohs.fhir.model.r4.terminologies.ResourceType

// all resources of a type
val patients = engine.search<Patient>(Search(ResourceType.Patient)).map { it.resource }

// filtered by a reference parameter
val encounters = engine.search<Encounter>(
  Search(ResourceType.Encounter).apply {
    filter(ReferenceClientParam("subject"), { value = "Patient/$patientId" })
  }
).map { it.resource }
```

The filter lambda sets the parameter's value. Cross-resource joins (for
example grouping observations by encounter) are done in memory after
searching, using the reference strings:

```kotlin
obs.subject?.reference?.value?.substringAfter("Patient/")
```

## Sync

Sync runs through a WorkManager worker you subclass:

```kotlin
import dev.ohs.fhir.engine.sync.AcceptLocalConflictResolver
import dev.ohs.fhir.engine.sync.ConflictResolver
import dev.ohs.fhir.engine.sync.DownloadWorkManager
import dev.ohs.fhir.engine.sync.FhirSyncWorker
import dev.ohs.fhir.engine.sync.download.ResourceParamsBasedDownloadWorkManager
import dev.ohs.fhir.engine.sync.upload.HttpCreateMethod
import dev.ohs.fhir.engine.sync.upload.HttpUpdateMethod
import dev.ohs.fhir.engine.sync.upload.UploadStrategy

class AppSyncWorker(appContext: Context, params: WorkerParameters) :
  FhirSyncWorker(appContext, params) {

  override fun getFhirEngine() = FhirEngineProvider.getInstance(applicationContext)

  override fun getDownloadWorkManager(): DownloadWorkManager =
    ResourceParamsBasedDownloadWorkManager(
      // which resource types to download, each with optional search params
      syncParams = mapOf(
        ResourceType.Patient to emptyMap(),
        ResourceType.Observation to emptyMap(),
      ),
      context = MyTimestampContext(applicationContext),
    )

  override fun getConflictResolver(): ConflictResolver = AcceptLocalConflictResolver

  override fun getUploadStrategy(): UploadStrategy =
    UploadStrategy.forIndividualRequest(
      methodForCreate = HttpCreateMethod.PUT,
      methodForUpdate = HttpUpdateMethod.PATCH,
      squash = true,
    )
}
```

The download manager needs a `TimestampContext` that persists per-type
`_lastUpdated` watermarks (note the interface method name is
`getLasUpdateTimestamp` - missing letter, as published):

```kotlin
class MyTimestampContext(private val context: Context) :
  ResourceParamsBasedDownloadWorkManager.TimestampContext {
  private val prefs
    get() = context.getSharedPreferences("sync_timestamps", Context.MODE_PRIVATE)
  override suspend fun saveLastUpdatedTimestamp(resourceType: ResourceType, timestamp: String?) {
    prefs.edit().putString(resourceType.name, timestamp).apply()
  }
  override suspend fun getLasUpdateTimestamp(resourceType: ResourceType): String? =
    prefs.getString(resourceType.name, null)
}
```

### Choosing the upload strategy

Prefer `UploadStrategy.forIndividualRequest(PUT, PATCH, squash = true)` with
client-assigned UUID ids. In 2.0.0-alpha02 the default transaction-bundle
upload generates `Bundle.entry.fullUrl` values that strict servers (HAPI
with request validation) reject with HTTP 422 `BUNDLE_ENTRY_URL_ABSOLUTE`.
Individual PUT-as-create requests avoid that path entirely.

### Triggering a sync and observing it

`Sync.oneTimeSync` returns a flow of `CurrentSyncJobStatus`; collect until a
terminal state:

```kotlin
import dev.ohs.fhir.engine.sync.CurrentSyncJobStatus
import dev.ohs.fhir.engine.sync.Sync

val terminal = Sync.oneTimeSync<AppSyncWorker>(context.applicationContext).first {
  it is CurrentSyncJobStatus.Succeeded ||
    it is CurrentSyncJobStatus.Failed ||
    it is CurrentSyncJobStatus.Cancelled
}
val ok = terminal is CurrentSyncJobStatus.Succeeded
```

To queue a sync behind an in-flight one (e.g. right after saving data), pass
a work policy:

```kotlin
Sync.oneTimeSync<AppSyncWorker>(
  context.applicationContext,
  existingWorkPolicy = ExistingWorkPolicy.APPEND_OR_REPLACE,
)
```

Failed sync work retries with exponential backoff under WorkManager rules; a
fresh app start enqueues new work. Sync errors (server rejections with
`OperationOutcome` bodies) appear in logcat - read them there when an upload
does not arrive on the server.
