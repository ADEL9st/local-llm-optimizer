# Local LLM Performance Doctor

> This tool does not make models magically faster. It diagnoses bottlenecks and recommends better runtime settings for your hardware.

> Unlike tools that only check hardware compatibility before running a model, **Local LLM Performance Doctor monitors your system during inference** and tells you exactly what's bottlenecking your performance.

Benchmarks local LLM runs, captures CPU / RAM / GPU / VRAM metrics in real time, and explains bottlenecks with diagnosis and advisor reports.

Supports **Ollama**, **LM Studio**, and any **OpenAI-compatible** backend.

---

## Features

- Real-time CPU, RAM, GPU utilization and VRAM tracking during inference
- Automatic bottleneck diagnosis (CPU-bound, GPU idle, VRAM pressure, etc.)
- Rule-grounded Advisor Agent with prioritized recommendations
- TR / EN language support
- Timestamped run output: `run.json`, `metrics.csv`, `report.md`

---

## Installation

```bash
pip install -e .
```

For development and testing:

```bash
pip install -e ".[dev]"
```

---

## Usage

**Ollama:**

```bash
doctor run --backend ollama --model llama3:latest --lang en --prompt "Explain local LLM performance in 5 steps."
```

**LM Studio:**

```bash
doctor run --backend lmstudio --model "model-id" --lang en --max-tokens 512
```

**OpenAI-compatible:**

```bash
doctor run --backend openai-compatible --base-url http://localhost:1234/v1 --model "model-id" --lang en
```

### Compare two runs

After running benchmarks, compare any two runs side by side. Pass either a run
directory or a `run.json` path:

```bash
doctor compare runs/2025-05-24_13-45-00 runs/2025-05-24_14-10-00 --lang en
```

```
=== Run Comparison ===
Run A: llama3:latest | ollama | Max tokens=n/a | runs/.../run.json
Run B: qwen2.5:7b    | ollama | Max tokens=n/a | runs/.../run.json

Metric                Run A    Run B    Diff      Better
--------------------  -------  -------  --------  ------
Duration (s)          20 s     10 s     -50.0%    B
Throughput (words/s)  10 w/s   20 w/s   +100.0%   B
RAM avg (%)           62 %     48 %     -22.6%    B
GPU avg (%)           8 %      66 %     +725.0%   B

--- Insights ---
- Run B is 100% faster (20.0 vs 10.0 words/s).
- Run B uses less RAM (avg 48% vs 62%).
- Run B keeps the GPU busier (avg 66% vs 8%).

--- Recommendation ---
Use Run B config for this machine.
```

### Hardware profile

Detect this machine's hardware and write a `hardware.json` profile:

```bash
doctor hardware --lang en --output hardware.json
```

```
=== Hardware Profile ===
OS     : Windows 10
CPU    : Intel(R) Core(TM) i5-10400 CPU @ 2.90GHz (6 cores / 12 threads)
RAM    : 32 GB
GPU    : NVIDIA GeForce GTX 1660
VRAM   : 6 GB
CUDA   : available (12.9)
Driver : 576.88
Python : 3.11.9

Saved to: hardware.json
```

When `nvidia-smi` or `psutil` is unavailable, the missing fields are reported under
a `Notes` section instead of failing. This profile can be reused by `doctor estimate`
with `--hardware hardware.json`.

### Estimate model fit

Predict whether a model will fit *before* you download or run it:

```bash
doctor estimate --model qwen2.5-32b --quant q4_k_m --context 4096 --lang en
```

```
=== Model Fit Estimate ===
Model          : qwen2.5-32b
Parameters     : 32 B
Quantization   : q4_k_m (4.85 bit/weight)
Context        : 4096 tokens
Weights        : 18.07 GB
KV cache       : 9.18 GB
Overhead       : 2.51 GB
Estimated need : 29.75 GB
Your VRAM      : 12 GB
Your RAM       : 32 GB

Status: does not fit GPU

--- Suggested ---
- Use a lower-bit quantization (for example q4 or q3).
- Choose a smaller model.
- Use CPU/RAM offload; the weights fit in system RAM.

--- Notes ---
- Estimates are approximate; KV cache and overhead are heuristic.
```

The parameter count is inferred from the model name; pass `--params 32` when it
cannot be parsed or when a model card reports a more accurate total. For names like
`mixtral-8x7b`, the estimator uses a conservative total expert-parameter estimate.
VRAM/RAM come from live
detection, a saved profile (`--hardware hardware.json`), or `--vram` / `--ram`
overrides. Estimates are heuristic and meant for planning, not exact numbers.

---

## Advisor Configuration

Stored in `run.json` under the `advisor` key:

```yaml
advisor:
  enabled: true
  mode: deterministic
  language: en   # en or tr
```

---

## Output

Each run produces a timestamped folder under `runs/`:

```
runs/
└── 2025-05-24_13-45-00/
    ├── run.json
    ├── metrics.csv
    └── report.md
```

---

## Sample Output

```
=== Local LLM Performance Doctor Report ===
Model   : llama3:latest
Backend : ollama
Duration: 12.4s
Samples : 12
Status  : Success

--- Diagnosis ---
[WARNING] GPU appears to be underutilized
  Average and peak GPU usage is low. Model may be running on CPU
  or the workload is not reaching the GPU.

--- Advisor Agent ---
Primary issue: GPU may not be in use.
This run suggests the model did not fully reach the GPU path during inference.

Evidence:
- Average GPU utilization: 4.0%
- Peak VRAM usage reached only 4.2% of available VRAM.

Prioritized Recommendations:
1. Check GPU acceleration settings in Ollama / LM Studio.
2. Verify NVIDIA driver and CUDA installation.
3. Re-run the same benchmark with GPU acceleration confirmed active.
```

---

## Running Tests

```bash
python -m pytest
```

Quiet output:

```bash
python -m pytest -q
```

---

## Changelog

### v0.6.0
- Promoted Ollama, LM Studio, and OpenAI-compatible backends to stable
- Friendly, actionable errors for connection-refused, timeout, HTTP, non-JSON, and empty-completion cases
- Surfaces the server's own error message when provided; reports under each backend's display name
- Consolidated result-building into a single `build_result` on the backend base
- Fixed MoE-style model-fit inference for names like `mixtral-8x7b`
- Added a backend unit test suite (mock backend remains the test fixture)

### v0.5.0
- Added `doctor estimate` to predict model fit before running
- Infers parameters from the model name; supports common quantizations
- Breaks down weights / KV cache / overhead vs. detected VRAM and RAM
- Fit status with suggestions: lower quant, reduce context, CPU/RAM offload, smaller model
- Reads limits from live detection, `hardware.json`, or `--vram`/`--ram`
- TR / EN output; estimates clearly labeled approximate

### v0.4.0
- Added `doctor hardware` to detect hardware and write `hardware.json`
- Captures OS, CPU (name + cores/threads), RAM, GPU, VRAM, driver, and CUDA availability/version
- Graceful notes when `nvidia-smi` or `psutil` is unavailable
- TR / EN hardware summary
- Used by `doctor estimate` via `--hardware hardware.json`

### v0.3.0
- Added `doctor compare` to compare two runs side by side
- Per-metric diff with a "better" verdict, plain-language insights, and a config recommendation
- TR / EN comparison output
- Accepts a run directory or a `run.json` path

### v0.2.0
- Added rule-grounded Advisor Agent
- Added prioritized recommendations
- Added TR / EN advisor output
- Integrated advisor into terminal and markdown reports
- Advisor does not modify runtime or system settings

### v0.1.2
- Fixed LM Studio `base_url` handling; `/v1` appended automatically if missing
- Clarified README examples
- Added sample run output

### v0.1.1
- Improved Windows NVIDIA collector reliability
- Better error messages when Ollama is not running
- Improved markdown report formatting

---

## License

AGPL-3.0 — see [LICENSE](LICENSE)

