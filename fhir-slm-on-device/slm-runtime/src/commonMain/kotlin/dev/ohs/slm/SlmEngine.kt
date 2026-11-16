package dev.ohs.slm

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlin.time.TimeSource

/** A small language model running on the device. One prompt in, streamed text out. */
interface SlmEngine {
    suspend fun load(modelPath: String)
    fun generate(prompt: String): Flow<String>

    /** The runtime's own numbers for the last finished [generate], or null if it has none. */
    fun lastRuntimeStats(): RuntimeStats?
    fun close()
}

/** Numbers the runtime reports for one generation. Token counts come from the model's tokenizer. */
data class RuntimeStats(
    val timeToFirstTokenMs: Long,
    val prefillTokens: Int,
    val decodeTokens: Int,
    val prefillTokensPerSecond: Double,
    val decodeTokensPerSecond: Double,
)

/** What one generation cost: our wall clock and memory, plus the runtime's numbers when it has them. */
data class GenerationStats(
    val timeToFirstChunkMs: Long,
    val totalMs: Long,
    val chars: Int,
    val peakRssMb: Long,
    val runtime: RuntimeStats?,
)

/** Peak resident memory of this process so far, in MB. */
expect fun peakRssMb(): Long

/** Streams the reply like [SlmEngine.generate] and reports its stats when the stream ends. */
fun SlmEngine.generateMeasured(prompt: String, onDone: (GenerationStats) -> Unit): Flow<String> = flow {
    val start = TimeSource.Monotonic.markNow()
    var firstMs = -1L
    var chars = 0
    generate(prompt).collect { chunk ->
        if (firstMs < 0) firstMs = start.elapsedNow().inWholeMilliseconds
        chars += chunk.length
        emit(chunk)
    }
    onDone(GenerationStats(firstMs, start.elapsedNow().inWholeMilliseconds, chars, peakRssMb(), lastRuntimeStats()))
}
