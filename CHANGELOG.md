# Changelog

## v0.6.0 - Backend Stability

- Promoted the Ollama, LM Studio, and OpenAI-compatible backends to stable.
- Hardened the OpenAI-compatible backend (which LM Studio extends): friendly, actionable messages for connection-refused, timeout, HTTP error, non-JSON, and empty-completion cases.
- Surfaces the server's own `error.message` when the API returns one; otherwise explains how to recover.
- Each backend reports under its own display name (e.g. "LM Studio") in error text.
- Consolidated duplicated result-building into a single `build_result` on the backend base class.
- Fixed model-fit parameter inference for MoE-style names such as `mixtral-8x7b` and names with active-parameter suffixes.
- Added a backend unit test suite covering success, error, and throughput paths (the mock backend remains the test fixture).

## v0.5.0 - Model Fit Estimator

- Added `llmopt estimate --model <name> --quant <q>` to predict whether a model fits before running it.
- Infers parameter count from the model name (override with `--params`); supports common quantizations.
- Breaks down weights, KV cache, and overhead into an estimated VRAM need and compares it to detected VRAM/RAM.
- Reports a fit status (fits / tight / does not fit) with actionable suggestions (lower quant, reduce context, CPU/RAM offload, smaller model).
- Reads limits from live detection, a saved `hardware.json` (`--hardware`), or `--vram`/`--ram` overrides.
- Estimates are clearly labeled approximate; flags mixture-of-experts names.
- TR/EN output via locale strings; added unit and CLI integration tests.

## v0.4.0 - Hardware Profile

- Added `llmopt hardware` to detect the machine and write a `hardware.json` profile.
- Captures OS, CPU name and core/thread counts, total RAM, GPU name, VRAM, driver, and CUDA availability/version.
- Reuses the NVIDIA collector's `nvidia-smi` discovery; degrades gracefully with notes when `nvidia-smi` or `psutil` is unavailable.
- TR/EN terminal summary via locale strings.
- Used by `llmopt estimate` via `--hardware hardware.json`.
- Added unit and CLI integration tests for the hardware profile.

## v0.3.0 - Compare Runs

- Added `llmopt compare <run_a> <run_b>` to compare two benchmark runs side by side.
- Compares duration, throughput, CPU/RAM/GPU averages, and VRAM usage from `run.json`.
- Direction-aware per-metric diff with a "better" verdict and a tie threshold.
- Plain-language insights (faster run, lower RAM, busier GPU) and a config recommendation.
- TR/EN comparison output via locale templates.
- Accepts either a run directory or a `run.json` path; tolerates missing diagnosis data.
- Added unit and CLI integration tests for the comparison feature.

## v0.2.0 - Advisor Agent MVP

- Added rule-grounded Advisor Agent.
- Added prioritized recommendations.
- Added TR/EN advisor output.
- Integrated advisor output into terminal and Markdown reports.
- Advisor does not modify runtime or system settings.
- Added `tests/` structure with unit and integration tests.
- Added diagnosis tests for GPU idle and RAM pressure.
- Added advisor unit tests and pipeline integration coverage.
- Added mock backend integration test for the full pipeline.
- Added sample metrics fixtures and sample run fixture.
- Added config validation for backend, prompt, model, timings, token limits, temperature, base URL handling, and advisor mode.

## v0.1.2

- Fix LM Studio `base_url` config handling.
- Add clearer README examples.
- Add sample run output.

## v0.1.1

- Fix Windows NVIDIA collector issues.
- Improve error messages when Ollama is not running.
- Improve Markdown report formatting.
