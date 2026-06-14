from __future__ import annotations

import argparse
import json
from pathlib import Path

from doctor import __version__
from doctor.compare import RunLoadError, compare_runs, load_run_summary
from doctor.compare.reporter import CompareReporter
from doctor.core.config import ConfigValidationError, RunConfig, load_locale
from doctor.estimate import DEFAULT_CONTEXT, DEFAULT_QUANT, EstimateError, estimate_fit
from doctor.estimate.reporter import EstimateReporter
from doctor.hardware import collect_hardware_profile, save_profile
from doctor.hardware.reporter import HardwareReporter
from doctor.core.pipeline import Pipeline
from doctor.core.registry import BACKEND_NAMES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llmopt",
        description="Local LLM Optimizer",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a benchmark and produce reports")
    run_parser.add_argument(
        "--backend",
        choices=BACKEND_NAMES,
        default="ollama",
        help="Benchmark backend",
    )
    run_parser.add_argument(
        "--model",
        default="llama3",
        help="Model name passed to the backend",
    )
    run_parser.add_argument(
        "--prompt",
        default="Explain what a Verilog module is in 5 bullet points.",
        help="Prompt sent to the model",
    )
    run_parser.add_argument(
        "--lang",
        choices=["tr", "en"],
        default="tr",
        help="Report language",
    )
    run_parser.add_argument(
        "--output-dir",
        default="runs",
        help="Directory where run artifacts will be written",
    )
    run_parser.add_argument(
        "--sample-interval",
        type=float,
        default=1.0,
        help="Metrics sampling interval in seconds",
    )
    run_parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Backend timeout in seconds",
    )
    run_parser.add_argument(
        "--base-url",
        default=None,
        help="OpenAI-compatible base URL, for example http://localhost:1234/v1",
    )
    run_parser.add_argument(
        "--api-key",
        default=None,
        help="Bearer token for OpenAI-compatible backends, if needed",
    )
    run_parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature for OpenAI-compatible backends",
    )
    run_parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum generated tokens for OpenAI-compatible backends",
    )

    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare two benchmark runs",
    )
    compare_parser.add_argument(
        "run_a",
        help="First run: a run directory or a run.json path",
    )
    compare_parser.add_argument(
        "run_b",
        help="Second run: a run directory or a run.json path",
    )
    compare_parser.add_argument(
        "--lang",
        choices=["tr", "en"],
        default="tr",
        help="Comparison report language",
    )

    hardware_parser = subparsers.add_parser(
        "hardware",
        help="Detect this machine's hardware and write a hardware profile",
    )
    hardware_parser.add_argument(
        "--lang",
        choices=["tr", "en"],
        default="tr",
        help="Hardware report language",
    )
    hardware_parser.add_argument(
        "--output",
        default="hardware.json",
        help="Path where the hardware profile JSON will be written",
    )

    estimate_parser = subparsers.add_parser(
        "estimate",
        help="Estimate whether a model fits this machine before running it",
    )
    estimate_parser.add_argument(
        "--model",
        required=True,
        help="Model name, for example qwen2.5-32b (used to infer parameter count)",
    )
    estimate_parser.add_argument(
        "--quant",
        default=DEFAULT_QUANT,
        help="Quantization, for example q4_k_m, q5_k_m, q8_0, f16",
    )
    estimate_parser.add_argument(
        "--context",
        type=int,
        default=DEFAULT_CONTEXT,
        help="Context length in tokens",
    )
    estimate_parser.add_argument(
        "--params",
        type=float,
        default=None,
        help="Parameter count in billions, overrides the value inferred from --model",
    )
    estimate_parser.add_argument(
        "--vram",
        type=float,
        default=None,
        help="Override detected VRAM in GB",
    )
    estimate_parser.add_argument(
        "--ram",
        type=float,
        default=None,
        help="Override detected RAM in GB",
    )
    estimate_parser.add_argument(
        "--hardware",
        default=None,
        help="Read VRAM/RAM from a saved hardware.json instead of detecting live",
    )
    estimate_parser.add_argument(
        "--lang",
        choices=["tr", "en"],
        default="tr",
        help="Estimate report language",
    )

    return parser


def config_from_args(args: argparse.Namespace) -> RunConfig:
    return RunConfig(
        backend=args.backend,
        model=args.model,
        prompt=args.prompt,
        lang=args.lang,
        output_dir=Path(args.output_dir),
        sample_interval=args.sample_interval,
        timeout_seconds=args.timeout,
        base_url=args.base_url,
        api_key=args.api_key,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            pipeline = Pipeline(config_from_args(args))
        except ConfigValidationError as exc:
            parser.exit(2, f"ERROR: {exc}\n")

        result = pipeline.run()
        return 0 if result.backend_result.success else 1

    if args.command == "compare":
        return run_compare(parser, args)

    if args.command == "hardware":
        return run_hardware(args)

    if args.command == "estimate":
        return run_estimate(parser, args)

    parser.error(f"Unknown command: {args.command}")
    return 2


def run_compare(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    locale = load_locale(args.lang)
    try:
        run_a = load_run_summary(Path(args.run_a), "A")
        run_b = load_run_summary(Path(args.run_b), "B")
    except RunLoadError as exc:
        parser.exit(2, f"ERROR: {exc}\n")

    result = compare_runs(run_a, run_b, locale)
    CompareReporter(locale).render(result)
    return 0


def run_hardware(args: argparse.Namespace) -> int:
    locale = load_locale(args.lang)
    profile = collect_hardware_profile()
    output_path = save_profile(profile, args.output)
    HardwareReporter(locale).render(profile, output_path)
    return 0


def run_estimate(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    locale = load_locale(args.lang)
    try:
        vram_gb, ram_gb = _resolve_hardware_limits(args)
        estimate = estimate_fit(
            args.model,
            params_billion=args.params,
            quant=args.quant,
            context_tokens=args.context,
            vram_gb=vram_gb,
            ram_gb=ram_gb,
        )
    except EstimateError as exc:
        parser.exit(2, f"ERROR: {exc}\n")

    EstimateReporter(locale).render(estimate)
    return 0


def _resolve_hardware_limits(
    args: argparse.Namespace,
) -> tuple[float | None, float | None]:
    if args.hardware:
        vram_gb, ram_gb = _limits_from_profile(Path(args.hardware))
    else:
        profile = collect_hardware_profile()
        gpu = profile.primary_gpu
        vram_gb = round(gpu.vram_total_mb / 1024, 2) if gpu and gpu.vram_total_mb else None
        ram_gb = profile.ram_total_gb

    if args.vram is not None:
        vram_gb = args.vram
    if args.ram is not None:
        ram_gb = args.ram
    return vram_gb, ram_gb


def _limits_from_profile(path: Path) -> tuple[float | None, float | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EstimateError(f"Could not read hardware profile {path}: {exc}") from exc

    gpus = data.get("gpus") or []
    vram_gb = None
    if gpus and isinstance(gpus[0], dict) and gpus[0].get("vram_total_mb"):
        vram_gb = round(gpus[0]["vram_total_mb"] / 1024, 2)
    ram_gb = data.get("ram_total_gb")
    return vram_gb, ram_gb
