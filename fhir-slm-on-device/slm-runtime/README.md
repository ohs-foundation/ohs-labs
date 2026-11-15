# slm-runtime

A Kotlin Multiplatform library that runs a small language model on device
through Google's [LiteRT-LM](https://github.com/google-ai-edge/LiteRT-LM)
and measures each run: tokens, speed, time to first token and memory.
[`slm-bench`](../slm-bench/) is the Android app that uses it.

## Targets

| Target | Status | LiteRT-LM artifact |
|---|---|---|
| Android (minSdk 24) | Works. Tested on the emulator | `com.google.ai.edge.litertlm:litertlm-android:0.18.0` |
| Desktop (JVM) | Works. Tested on macOS | `com.google.ai.edge.litertlm:litertlm-jvm:0.18.0` |
| iOS | Not started. LiteRT-LM's iOS API is Swift only and in early preview | None |

Both targets share one source folder, `src/litertMain/kotlin`, because
LiteRT-LM has the same Kotlin API on Android and the JVM.

## Add it to a project

The library is not published. Include it as a composite build.

In `settings.gradle.kts`:

```kotlin
includeBuild("../slm-runtime")
```

In the module's `build.gradle.kts`:

```kotlin
dependencies {
    implementation("dev.ohs.slm:slm-runtime:0.1.0")
}
```

## Use it

```kotlin
val engine = LiteRtLmEngine(
    cacheDir = context.cacheDir.path,
    backend = Backend.CPU(),
    maxNumTokens = 8192,
)
engine.load("/path/to/gemma-4-E2B-it.litertlm")

engine.generateMeasured("Summarize this patient record.") { stats ->
    println("${stats.runtime?.prefillTokens} tokens in, ${stats.totalMs} ms")
}.collect { chunk -> print(chunk) }

engine.close()
```

`load` reads a 2.6 GB file, so call it once and reuse the engine. Each
`generate` call starts a fresh conversation, so nothing carries over
between prompts.

## API

| Name | What it is |
|---|---|
| `SlmEngine` | Interface: `load(modelPath)`, `generate(prompt): Flow<String>`, `lastRuntimeStats()`, `close()` |
| `LiteRtLmEngine` | `SlmEngine` on LiteRT-LM. All calls run on one thread, which LiteRT-LM requires |
| `SlmEngine.generateMeasured(prompt, onDone)` | Like `generate`, and calls `onDone` with a `GenerationStats` when the reply ends |
| `GenerationStats` | `timeToFirstChunkMs`, `totalMs`, `chars`, `peakRssMb`, and `runtime` |
| `RuntimeStats` | Numbers from LiteRT-LM: `timeToFirstTokenMs`, `prefillTokens`, `decodeTokens`, `prefillTokensPerSecond`, `decodeTokensPerSecond` |
| `peakRssMb()` | Peak memory of the current process, in MB |

`LiteRtLmEngine` options:

| Option | Meaning | Default |
|---|---|---|
| `cacheDir` | Folder where LiteRT-LM can write cache files | Required |
| `backend` | `Backend.CPU()` or `Backend.GPU()` | `Backend.CPU()` |
| `maxNumTokens` | Context size, prompt plus reply | `null`, the model's default (4,096 for Gemma 4 E2B) |

## Build and test

```bash
./gradlew build
```

`DesktopSmokeTest` loads the model on the computer and asks for a one
sentence hello. It is skipped unless `SLM_MODEL` points to a model file.

```bash
SLM_MODEL=~/models/gemma-4-E2B-it.litertlm ./gradlew jvmTest --tests dev.ohs.slm.DesktopSmokeTest
```

## Limits

- Token counts and speeds come from LiteRT-LM's `getBenchmarkInfo()`, an
  experimental API. A LiteRT-LM update may change or remove it.
- The GPU backend needs OpenCL. The Android emulator doesn't have it.
- `peakRssMb()` reads the true peak on Android and Linux. macOS has no
  `/proc`, so there it reports the current memory, which can be lower
  than the peak.
- No way to cancel a reply or set sampling options (temperature, top k)
  yet.
