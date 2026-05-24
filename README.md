# Local LLM Performance Doctor

> ⚠️ **Early development.** Ollama backend is functional. LM Studio and OpenAI-compatible backends are experimental — behavior may be unstable or incomplete.

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
