package dev.ohs.slm

import com.google.ai.edge.litertlm.Backend
import com.google.ai.edge.litertlm.ConversationConfig
import com.google.ai.edge.litertlm.Engine
import com.google.ai.edge.litertlm.EngineConfig
import java.io.File
import java.util.concurrent.Executors
import kotlinx.coroutines.asCoroutineDispatcher
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext

/**
 * [SlmEngine] on Google LiteRT-LM. LiteRT-LM wants one thread to own the engine,
 * so every call runs on a single-thread dispatcher.
 */
class LiteRtLmEngine(
    private val cacheDir: String,
    private val backend: Backend = Backend.CPU(),
) : SlmEngine {
    private val executor = Executors.newSingleThreadExecutor()
    private val dispatcher = executor.asCoroutineDispatcher()
    private var engine: Engine? = null

    override suspend fun load(modelPath: String) = withContext(dispatcher) {
        if (engine != null) return@withContext
        val config = EngineConfig(modelPath = modelPath, backend = backend, cacheDir = cacheDir)
        // Store it only after initialize returns, closing a failed engine throws.
        engine = Engine(config).also { it.initialize() }
    }

    // A fresh conversation per prompt, so no history leaks between runs.
    override fun generate(prompt: String): Flow<String> = flow {
        val conversation = checkNotNull(engine) { "Call load first" }.createConversation(ConversationConfig())
        try {
            conversation.sendMessageAsync(prompt).collect { emit(it.toString()) }
        } finally {
            conversation.close()
        }
    }.flowOn(dispatcher)

    override fun close() {
        executor.execute {
            engine?.close()
            engine = null
        }
        executor.shutdown()
    }
}

actual fun peakRssMb(): Long =
    File("/proc/self/status").readLines()
        .firstOrNull { it.startsWith("VmHWM:") }
        ?.filter(Char::isDigit)?.toLongOrNull()?.div(1024) ?: -1
