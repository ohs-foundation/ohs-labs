package dev.ohs.slm.smoketest

import android.app.Application
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.google.ai.edge.litertlm.Backend
import dev.ohs.slm.GenerationStats
import dev.ohs.slm.LiteRtLmEngine
import dev.ohs.slm.generateMeasured
import java.io.File
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Benchmark runs are started from adb, one cold start per run:
 *   adb shell am start -S -n dev.ohs.slm.smoketest/.MainActivity --es prompt_file p.txt --ei max_tokens 4096 --es backend gpu
 * prompt_file is a file in the app's files dir. The result is one logcat line with the tag SlmBench,
 * and the reply is saved next to the prompt as <prompt_file>.reply.txt.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        BenchRequest.promptFile = intent.getStringExtra("prompt_file")
        BenchRequest.maxTokens = intent.getIntExtra("max_tokens", 0).takeIf { it > 0 }
        BenchRequest.gpu = intent.getStringExtra("backend") == "gpu"
        setContent { MaterialTheme { SmokeTestScreen() } }
    }
}

/** What the launching intent asked for. Read once by the ViewModel when it is created. */
object BenchRequest {
    var promptFile: String? = null
    var maxTokens: Int? = null
    var gpu: Boolean = false
}

data class UiState(
    val status: String = "Loading model…",
    val ready: Boolean = false,
    val busy: Boolean = false,
    val reply: String = "",
    val stats: GenerationStats? = null,
)

class SmokeTestViewModel(app: Application) : AndroidViewModel(app) {
    // Copy the model here with: adb shell run-as dev.ohs.slm.smoketest cp /data/local/tmp/model.litertlm files/
    private val modelFile = File(app.filesDir, "model.litertlm")
    private val maxTokens = BenchRequest.maxTokens
    private val backendName = if (BenchRequest.gpu) "gpu" else "cpu"
    private val engine = LiteRtLmEngine(
        cacheDir = app.cacheDir.path,
        backend = if (BenchRequest.gpu) Backend.GPU() else Backend.CPU(),
        maxNumTokens = maxTokens,
    )
    private var loadMs = 0L
    private val _state = MutableStateFlow(UiState())
    val state = _state.asStateFlow()

    init {
        viewModelScope.launch {
            if (!modelFile.exists()) {
                _state.update { it.copy(status = "No model at ${modelFile.path}") }
                return@launch
            }
            val ms = runCatching { kotlin.system.measureTimeMillis { engine.load(modelFile.path) } }
                .onFailure { e -> _state.update { it.copy(status = "Load failed: ${e.message}") } }
                .getOrNull() ?: return@launch
            loadMs = ms
            Log.i(TAG, "model loaded in $ms ms")
            _state.update { it.copy(status = "Model loaded in ${ms / 1000.0} s (${backendName.uppercase()})", ready = true) }
            BenchRequest.promptFile?.let { send(File(app.filesDir, it).readText(), it) }
        }
    }

    fun send(prompt: String, benchName: String? = null) {
        if (!_state.value.ready || _state.value.busy) return
        _state.update { it.copy(busy = true, reply = "", stats = null) }
        viewModelScope.launch {
            runCatching {
                engine.generateMeasured(prompt) { stats ->
                    Log.i(TAG, "stats $stats")
                    if (benchName != null) Log.i(BENCH_TAG, benchLine(benchName, stats))
                    _state.update { it.copy(stats = stats) }
                }.collect { chunk -> _state.update { it.copy(reply = it.reply + chunk) } }
                if (benchName != null) File(getApplication<Application>().filesDir, "$benchName.reply.txt").writeText(_state.value.reply)
            }.onFailure { e ->
                if (benchName != null) Log.i(BENCH_TAG, "prompt=$benchName error=${e.message?.replace(' ', '_')}")
                _state.update { it.copy(reply = it.reply + "\n[error: ${e.message}]") }
            }
            _state.update { it.copy(busy = false) }
        }
    }

    // One line per run, key=value, so a script can collect the results.
    private fun benchLine(name: String, s: GenerationStats): String {
        val r = s.runtime
        return "prompt=$name backend=$backendName max_tokens=${maxTokens ?: "default"} load_ms=$loadMs " +
            "ttft_ms=${r?.timeToFirstTokenMs} prefill_tokens=${r?.prefillTokens} decode_tokens=${r?.decodeTokens} " +
            "prefill_tps=${r?.prefillTokensPerSecond?.let { "%.1f".format(it) }} " +
            "decode_tps=${r?.decodeTokensPerSecond?.let { "%.1f".format(it) }} " +
            "total_ms=${s.totalMs} first_chunk_ms=${s.timeToFirstChunkMs} chars=${s.chars} peak_rss_mb=${s.peakRssMb}"
    }

    override fun onCleared() = engine.close()

    companion object {
        const val TAG = "SlmSmoke"
        const val BENCH_TAG = "SlmBench"
    }
}

@Composable
fun SmokeTestScreen(vm: SmokeTestViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()
    var prompt by remember { mutableStateOf("Say hello in one sentence.") }
    Column(Modifier.fillMaxSize().padding(16.dp).padding(top = 32.dp)) {
        Text(state.status, style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(prompt, { prompt = it }, Modifier.padding(bottom = 8.dp))
        Button(onClick = { vm.send(prompt) }, enabled = state.ready && !state.busy) {
            Text(if (state.busy) "Generating…" else "Send")
        }
        state.stats?.let {
            Text(
                "TTFT ${it.runtime?.timeToFirstTokenMs} ms · total ${it.totalMs} ms · " +
                    "prompt ${it.runtime?.prefillTokens} tok · reply ${it.runtime?.decodeTokens} tok · " +
                    "decode ${it.runtime?.decodeTokensPerSecond?.let { "%.1f".format(it) }} tok/s · peak RSS ${it.peakRssMb} MB",
                style = MaterialTheme.typography.bodySmall,
            )
        }
        Spacer(Modifier.height(8.dp))
        Text(state.reply, Modifier.verticalScroll(rememberScrollState()))
    }
}
