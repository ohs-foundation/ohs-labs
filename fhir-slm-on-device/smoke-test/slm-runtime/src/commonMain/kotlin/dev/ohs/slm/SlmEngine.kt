package dev.ohs.slm

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlin.time.TimeSource

/** A small language model running on the device. One prompt in, streamed text out. */
interface SlmEngine {
    suspend fun load(modelPath: String)
    fun generate(prompt: String): Flow<String>
    fun close()
}

/** What one generation cost. Chunks are what the runtime streamed, not tokens. */
data class GenerationStats(
    val timeToFirstChunkMs: Long,
    val totalMs: Long,
    val chunks: Int,
    val chars: Int,
    val peakRssMb: Long,
)

/** Peak resident memory of this process so far, in MB. */
expect fun peakRssMb(): Long

/** Streams the reply like [SlmEngine.generate] and reports its stats when the stream ends. */
fun SlmEngine.generateMeasured(prompt: String, onDone: (GenerationStats) -> Unit): Flow<String> = flow {
    val start = TimeSource.Monotonic.markNow()
    var firstMs = -1L
    var chunks = 0
    var chars = 0
    generate(prompt).collect { chunk ->
        if (firstMs < 0) firstMs = start.elapsedNow().inWholeMilliseconds
        chunks++
        chars += chunk.length
        emit(chunk)
    }
    onDone(GenerationStats(firstMs, start.elapsedNow().inWholeMilliseconds, chunks, chars, peakRssMb()))
}
