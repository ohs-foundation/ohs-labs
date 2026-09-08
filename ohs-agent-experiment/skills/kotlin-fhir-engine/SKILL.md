---
name: kotlin-fhir-engine
description: Using dev.ohs.fhir:fhir-engine on Android - local FHIR database (create, get, search with typed filters), bidirectional sync with a FHIR server via WorkManager (one-time and periodic), auth, config, progress, and a sync troubleshooting guide. Use when storing FHIR resources on-device, querying them, or syncing with a server. All API in this file is verified against the engine source at tag v2.0.0-alpha02.
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

The engine is built with a JDK 21 toolchain and requires the consuming app to set `jvmTarget = 21` (the reference ANC app had to bump from 17 to 21 for this dependency). This is the OHS library that drives the app-wide 21 requirement.

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
      this,   // the platformContext; on Android pass the application Context
    )
  }
}
```

Keep the trailing slash on `baseUrl`. Calling `init` a second time throws
`IllegalStateException`. Plain-HTTP servers (dev setups, and the Android
emulator reaching the host machine at `http://10.0.2.2:...`) also need
cleartext traffic enabled, e.g. in the manifest:

```xml
<application android:usesCleartextTraffic="true" ...>
```

Get the engine anywhere with:

```kotlin
val engine = FhirEngineProvider.getInstance(context.applicationContext)
```

### Full configuration surface

`FhirEngineConfiguration` and `ServerConfiguration` (all fields with their
defaults):

```kotlin
data class FhirEngineConfiguration(
  val enableEncryptionIfSupported: Boolean = false,
  val databaseErrorStrategy: DatabaseErrorStrategy = DatabaseErrorStrategy.UNSPECIFIED,
  val serverConfiguration: ServerConfiguration? = null,   // null = local-only, no sync
  val testMode: Boolean = false,
  val customSearchParameters: List<SearchParamDefinition>? = null,
  val storageDirectory: String? = null,
)
enum class DatabaseErrorStrategy { UNSPECIFIED, RECREATE_AT_OPEN }

data class ServerConfiguration(
  val baseUrl: String,
  val networkConfiguration: NetworkConfiguration = NetworkConfiguration(),
  val authenticator: HttpAuthenticator? = null,   // see Auth below
  val httpLogger: HttpLogger = HttpLogger.NONE,
)
data class NetworkConfiguration(
  val connectionTimeOut: Long = 10,   // seconds
  val readTimeOut: Long = 10,
  val writeTimeOut: Long = 10,
  val uploadWithGzip: Boolean = false,
  val httpCache: CacheConfiguration? = null,
)
```

To see the HTTP traffic while debugging sync, raise the logger level:

```kotlin
import dev.ohs.fhir.engine.sync.remote.HttpLogger
httpLogger = HttpLogger(level = HttpLogger.Level.BODY)   // NONE | BASIC | HEADERS | BODY
```

## Auth (syncing against a protected server)

`HttpAuthenticator` is a functional interface returning the method to use.
Supply a bearer token or basic credentials via `ServerConfiguration`:

```kotlin
import dev.ohs.fhir.engine.sync.HttpAuthenticator
import dev.ohs.fhir.engine.sync.HttpAuthenticationMethod

ServerConfiguration(
  baseUrl = "https://server.example/fhir/",
  authenticator = HttpAuthenticator { HttpAuthenticationMethod.Bearer(currentAccessToken()) },
)
// or HttpAuthenticationMethod.Basic(username, password)
```

`getAuthenticationMethod()` is called per request, so returning a freshly
read token (e.g. from secure storage) is how you handle token refresh.

## Local CRUD

```kotlin
import dev.ohs.fhir.engine.get

// create is vararg and returns the assigned ids. Assign UUIDs yourself so
// references (Encounter/<id> inside an Observation) stay valid before and
// after upload, and so PUT-as-create works (see Upload strategy).
val encounter = Encounter(id = UUID.randomUUID().toString(), ...)
val ids: List<String> = engine.create(encounter, observation1, observation2)

val patient: Patient = engine.get<Patient>("patient-id")   // reified extension; throws if absent
engine.update(editedPatient)                               // vararg
engine.delete(ResourceType.Patient, "patient-id")
val n: Long = engine.count(Search(ResourceType.Patient))
```

Other engine methods: `getLastSyncTimeStamp(): OffsetDateTime?`,
`clearDatabase()`, `purge(type, id, forcePurge = false)` and its
`Set<String>` overload, `getLocalChanges(type, id): List<LocalChange>`, and
`withTransaction { ... }` to batch several writes atomically.

## Search

`engine.search<T>(Search(resourceType))` returns `List<SearchResult<T>>`;
each result's `.resource` is the model object; `.included` holds any
`_include` matches and `.revIncluded` any `_revinclude` matches.

```kotlin
import dev.ohs.fhir.engine.search.Search
import dev.ohs.fhir.engine.search.ReferenceClientParam
import dev.ohs.fhir.engine.search.TokenClientParam
import dev.ohs.fhir.engine.search.DateClientParam
import dev.ohs.fhir.engine.search.StringClientParam
import dev.ohs.fhir.engine.search.Order
import dev.ohs.fhir.model.r4.terminologies.ResourceType

// all of a type
val patients = engine.search<Patient>(Search(ResourceType.Patient)).map { it.resource }
```

Filters are typed: there is one `filter(...)` overload per FHIR search
parameter kind, each taking one or more criterion lambdas. The seven
parameter types are `StringClientParam`, `TokenClientParam`,
`ReferenceClientParam`, `DateClientParam`, `NumberClientParam`,
`QuantityClientParam`, `UriClientParam` - each constructed with the search
parameter name, e.g. `TokenClientParam("code")`.

```kotlin
// reference: by subject
engine.search<Observation>(
  Search(ResourceType.Observation).apply {
    filter(ReferenceClientParam("subject"), { value = "Patient/$patientId" })
  }
)

// token: observations with a specific LOINC code
Search(ResourceType.Observation).apply {
  filter(TokenClientParam("code"), { value = of(Code(value = "29463-7")) })  // of(...) builds the token value
}

// date: visits from a cutoff. SearchComparator is nested in the model:
// import dev.ohs.fhir.model.r4.SearchParameter.SearchComparator  (Eq, Gt, Ge, Lt, Le, Ne, Sa, Eb, Ap)
Search(ResourceType.Encounter).apply {
  filter(DateClientParam("date"), {
    prefix = SearchComparator.Ge
    value = of(FhirDateTime.fromString("2026-09-01"))
  })
}

// string: name starts-with / contains / exact via the modifier
Search(ResourceType.Patient).apply {
  filter(StringClientParam("name"), { modifier = StringFilterModifier.CONTAINS; value = "car" })
}
```

Criterion properties per type: string has `value` + `modifier`
(`STARTS_WITH` default, `MATCHES_EXACTLY`, `CONTAINS`); token has `value`
set via `of(code/string/Coding/CodeableConcept/Identifier/...)`; reference
and uri have `value: String`; date has `prefix: SearchComparator` +
`value` via `of(FhirDate)`/`of(FhirDateTime)`; number has `prefix` +
`value: BigDecimal`; quantity has `prefix`, `value: BigDecimal`, `system`,
`unit`. That `BigDecimal` is the ionspin KMP type
(`com.ionspin.kotlin.bignum.decimal.BigDecimal`), the same one the model
classes use, not `java.math.BigDecimal` - importing the Java one will not
compile.

Multiple criteria in one `filter(...)` are combined with `Operation.OR` by
default; the trailing `operation` argument must be passed by name to change
it. Multiple separate `filter(...)` calls are combined with `Operation.AND`
(the Search-level default).

Sort and paging:

```kotlin
Search(ResourceType.Encounter, count = 20, from = 0).apply {   // page size + offset
  filter(ReferenceClientParam("subject"), { value = "Patient/$patientId" })
  sort(DateClientParam("date"), Order.DESCENDING)              // also StringClientParam / NumberClientParam
}
```

Cross-resource joins can be done with `_include` (`Search.include<T>(...)`)
and reverse chaining (`Search.has<T>(...)`), or simply in memory after
searching, using the reference strings:

```kotlin
obs.subject?.reference?.value?.substringAfter("Patient/")
```

## Sync

Sync is the part that goes wrong most often in practice. Read this whole
section before wiring it. Three rules cover most failures.

1. Sync never triggers itself. If nothing in the app calls
   `Sync.oneTimeSync`, no data ever moves in either direction. The app
   compiles, runs, and shows an empty list forever.
2. Only the resource types you list in the download manager are
   downloaded. Forgetting `Questionnaire` there means the visit form
   never arrives.
3. Prefer individual PUT requests for upload. `getUploadStrategy()` is
   abstract, so there is no default, but the engine's own sample
   workers (`DemoFhirSyncWorker`) use `forBundleRequest`, and that
   bundle upload is rejected by strict servers in 2.0.0-alpha02. Do not
   copy the sample; use `forIndividualRequest` (details below).

### The sync worker

Sync runs through a WorkManager worker you subclass. All four
`getX()` methods are abstract and must be overridden:

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
      // EVERY type the app needs must be listed here, including Questionnaire
      syncParams = mapOf(
        ResourceType.Patient to emptyMap(),
        ResourceType.Encounter to emptyMap(),
        ResourceType.Observation to emptyMap(),
        ResourceType.Questionnaire to emptyMap(),
      ),
      context = MyTimestampContext(applicationContext),
    )

  override fun getConflictResolver(): ConflictResolver = AcceptLocalConflictResolver
  // provided: AcceptLocalConflictResolver, AcceptRemoteConflictResolver (top-level vals);
  // or write your own: ConflictResolver { local, remote -> Resolved(local) }

  override fun getUploadStrategy(): UploadStrategy =
    UploadStrategy.forIndividualRequest(
      methodForCreate = HttpCreateMethod.PUT,
      methodForUpdate = HttpUpdateMethod.PATCH,
      squash = true,
    )
}
```

### Choosing the upload strategy

`UploadStrategy` has a private constructor; you get one only from the two
factory functions, `forIndividualRequest(methodForCreate, methodForUpdate,
squash)` and `forBundleRequest(methodForCreate, methodForUpdate, squash,
bundleSize)`. The reasoning for the individual choice, piece by piece:

- **Individual requests, not a bundle.** In 2.0.0-alpha02 the bundle
  upload generates `Bundle.entry.fullUrl` values that strict servers
  (HAPI with request validation) reject with HTTP 422
  `BUNDLE_ENTRY_URL_ABSOLUTE`. Individual requests avoid that code path
  entirely. The engine's own sample workers (`DemoFhirSyncWorker`) use
  `forBundleRequest`, so copying the sample is exactly how you hit this.
- **PUT for create, not POST.** `HttpCreateMethod` has `PUT` and `POST`.
  PUT-as-create tells the server "store this resource under the id I
  chose", so the client-assigned UUIDs and every local reference between
  resources stay valid on the server. POST asks the server to assign a
  new id, which breaks the references the app already saved locally.
- **PATCH for update, not PUT.** `HttpUpdateMethod` has `PUT` and
  `PATCH`, but passing `HttpUpdateMethod.PUT` throws `NotImplementedError`
  at 2.0.0-alpha02 ("PUT for UPDATE not supported yet"). Use `PATCH`.
- **squash = true.** Multiple local edits to the same resource collapse
  into one request. Combined with PUT-as-create this means a freshly
  created and then edited resource still uploads as a single PUT, so the
  PATCH path (which requires the server to support JSON Patch) is rarely
  exercised. `squash = false` is also rejected for `forBundleRequest`,
  so keep it true.

### Download watermarks

The download manager needs a `TimestampContext` that persists per-type
`_lastUpdated` watermarks. Mind the mismatched method names, verified in
the interface at 2.0.0-alpha02: the setter is spelled correctly
(`saveLastUpdatedTimestamp`) but the getter is misspelled
(`getLasUpdateTimestamp`, missing a `t` and the `d`). Override both
exactly as spelled or the override does not compile:

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

Watermarks make later downloads incremental: each sync only fetches
resources updated since the saved timestamp. Two consequences to know:

- A first sync against an empty or misconfigured server still saves a
  watermark. If the server is populated afterward with resources whose
  update time is older than the watermark, later syncs will not fetch
  them. During development, clearing the app's data (or the prefs file
  holding the watermarks) forces a full re-download.
- Watermarks are per resource type, so adding a new type to
  `syncParams` later starts that type from a full download.

### Triggering a one-time sync (this is on you)

The engine ships the worker but nothing schedules it. Wire two triggers
as a baseline:

```kotlin
import dev.ohs.fhir.engine.sync.CurrentSyncJobStatus
import dev.ohs.fhir.engine.sync.Sync

// 1. On app start (e.g. from the first screen's ViewModel):
//    collect until a terminal state so you can react to the outcome
val terminal = Sync.oneTimeSync<AppSyncWorker>(context.applicationContext).first {
  it is CurrentSyncJobStatus.Succeeded ||
    it is CurrentSyncJobStatus.Failed ||
    it is CurrentSyncJobStatus.Cancelled
}
val ok = terminal is CurrentSyncJobStatus.Succeeded
// refresh the UI from the local database after a successful sync

// 2. Right after saving data, queue an upload behind any in-flight sync.
//    existingWorkPolicy MUST be named: oneTimeSync's signature is
//    oneTimeSync(context, retryConfiguration = ..., existingWorkPolicy = ...),
//    so a positional second argument would bind to retryConfiguration.
Sync.oneTimeSync<AppSyncWorker>(
  context.applicationContext,
  existingWorkPolicy = ExistingWorkPolicy.APPEND_OR_REPLACE,
)
```

The signature is
`oneTimeSync<W>(context, retryConfiguration = defaultRetryConfiguration,
existingWorkPolicy = ExistingWorkPolicy.KEEP): Flow<CurrentSyncJobStatus>`.
So the default policy is `KEEP` (see the retry note below for why that
matters). Collect the returned flow with a terminal-state filter as above;
an open-ended `collect { }` on it never returns and silently hangs the
calling coroutine.

`CurrentSyncJobStatus` states: `Enqueued`, `Running(inProgressSyncJob)`,
`Succeeded(timestamp)`, `Failed(timestamp)`, `Cancelled`, `Blocked`.

### Progress

The `Running` state carries a `SyncJobStatus`, whose `InProgress` variant
reports counts, so you can drive a progress bar:

```kotlin
when (val s = status) {
  is CurrentSyncJobStatus.Running -> {
    val job = s.inProgressSyncJob
    if (job is SyncJobStatus.InProgress) {
      // job.syncOperation is SyncOperation.DOWNLOAD or SyncOperation.UPLOAD
      val fraction = if (job.total > 0) job.completed.toFloat() / job.total else 0f
    }
  }
  else -> {}
}
```

### Periodic (background) sync

For recurring background sync use `Sync.periodicSync` with a
`PeriodicSyncConfiguration`:

```kotlin
import dev.ohs.fhir.engine.sync.Sync
import dev.ohs.fhir.engine.sync.PeriodicSyncConfiguration
import dev.ohs.fhir.engine.sync.RepeatInterval
import kotlin.time.Duration.Companion.hours

Sync.periodicSync<AppSyncWorker>(
  context.applicationContext,
  PeriodicSyncConfiguration(
    repeat = RepeatInterval(interval = 6.hours),
    // syncConstraints = SyncConstraints(requiredNetworkType = NetworkType.UNMETERED),
  ),
)   // returns Flow<PeriodicSyncJobStatus>
```

### Retry behavior when uploads fail

`RetryConfiguration` controls retries. The default,
`defaultRetryConfiguration`, is **LINEAR backoff, 30-second delay, 3
retries** (not exponential). Two behaviors observed in practice:

- Once the work has exhausted its retries, re-enqueueing with the default
  `KEEP` policy keeps the dead work and nothing more happens. A fresh app
  start (or an explicit new `oneTimeSync`) enqueues new work and retries
  the pending upload.
- Local data is never lost by a failed upload. It stays in the local
  database, the app keeps showing it, and the next successful sync
  uploads it. The failure is only visible on the server side (the
  resource is missing there) and in logcat.

Server rejections (`OperationOutcome` bodies) appear in logcat - read
them there when an upload does not arrive on the server. They state
exactly which element the server refused and why.

### Sync troubleshooting checklist

| Symptom | Likely cause | Fix |
|---|---|---|
| App shows an empty list forever, no errors | Sync is never triggered - nothing calls `Sync.oneTimeSync` | Wire the app-start trigger above |
| Visit form never appears | `Questionnaire` missing from `syncParams` | Add it to the download map |
| Upload rejected, HTTP 422 mentioning `fullUrl` | Using `forBundleRequest` (the sample's default) against a strict server | `UploadStrategy.forIndividualRequest(PUT, PATCH, squash = true)` |
| `NotImplementedError: PUT for UPDATE` at runtime | `methodForUpdate = HttpUpdateMethod.PUT` | Use `HttpUpdateMethod.PATCH` |
| References broken on the server after upload | POST-as-create let the server reassign ids | Use client UUIDs + `HttpCreateMethod.PUT` |
| Override does not compile on the timestamp context | Wrong method name - it is `getLasUpdateTimestamp` (typo) and `saveLastUpdatedTimestamp` | Copy both names exactly |
| Download returns nothing although the server has data | Stale `_lastUpdated` watermark from an earlier sync | Clear app data or the watermark prefs, re-sync |
| Saved visit shown in app but missing on server | Upload failed and is retrying (or retries exhausted) | Check logcat for the `OperationOutcome`; restart the app or enqueue a new sync |
| `existingWorkPolicy` seems ignored | Passed positionally, so it bound to `retryConfiguration` | Pass it by name |
| Sync coroutine never completes | Open-ended `collect { }` on the status flow | Collect with a terminal-state filter (`first { ... }`) |
| All requests fail instantly on emulator | Wrong host or cleartext HTTP blocked | Use `http://10.0.2.2:<port>/fhir/` and enable cleartext traffic |
| 401 / auth failures against a real server | No `authenticator` on `ServerConfiguration` | Supply `HttpAuthenticator { HttpAuthenticationMethod.Bearer(token) }` |
