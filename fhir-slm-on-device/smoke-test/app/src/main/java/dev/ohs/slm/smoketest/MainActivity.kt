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
import dev.ohs.slm.GenerationStats
import dev.ohs.slm.LiteRtLmEngine
import dev.ohs.slm.generateMeasured
import java.io.File
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { SmokeTestScreen() } }
    }
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
    private val engine = LiteRtLmEngine(cacheDir = app.cacheDir.path)
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
            Log.i(TAG, "model loaded in $ms ms")
            _state.update { it.copy(status = "Model loaded in ${ms / 1000.0} s (CPU)", ready = true) }
        }
    }

    fun send(prompt: String) {
        if (!_state.value.ready || _state.value.busy) return
        _state.update { it.copy(busy = true, reply = "", stats = null) }
        viewModelScope.launch {
            runCatching {
                engine.generateMeasured(prompt) { stats ->
                    Log.i(TAG, "stats $stats")
                    _state.update { it.copy(stats = stats) }
                }.collect { chunk -> _state.update { it.copy(reply = it.reply + chunk) } }
            }.onFailure { e -> _state.update { it.copy(reply = it.reply + "\n[error: ${e.message}]") } }
            _state.update { it.copy(busy = false) }
        }
    }

    override fun onCleared() = engine.close()

    companion object {
        const val TAG = "SlmSmoke"
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
                "First chunk ${it.timeToFirstChunkMs} ms · total ${it.totalMs} ms · " +
                    "${it.chunks} chunks · ${it.chars} chars · peak RSS ${it.peakRssMb} MB",
                style = MaterialTheme.typography.bodySmall,
            )
        }
        Spacer(Modifier.height(8.dp))
        Text(state.reply, Modifier.verticalScroll(rememberScrollState()))
    }
}
