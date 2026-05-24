# Changelog

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
