package dev.ohs.slm

import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.runBlocking
import java.io.File
import kotlin.test.Test
import kotlin.test.assertTrue

/**
 * Runs the model on the desktop. Skipped unless SLM_MODEL points at a .litertlm file:
 *   SLM_MODEL=~/models/gemma-4-E2B-it.litertlm ./gradlew jvmTest --tests dev.ohs.slm.DesktopSmokeTest
 */
class DesktopSmokeTest {
    @Test
    fun saysHello() = runBlocking {
        val model = System.getenv("SLM_MODEL")?.takeIf { File(it).exists() } ?: return@runBlocking
        val engine = LiteRtLmEngine(cacheDir = System.getProperty("java.io.tmpdir"))
        engine.load(model)
        var stats: GenerationStats? = null
        val reply = engine.generateMeasured("Say hello in one sentence.") { stats = it }.toList().joinToString("")
        engine.close()
        println("reply: $reply")
        println("stats: $stats")
        assertTrue(reply.isNotBlank())
        assertTrue((stats?.runtime?.decodeTokens ?: 0) > 0)
    }
}
