from __future__ import annotations

import argparse
from pathlib import Path

from doctor import __version__
from doctor.core.config import ConfigValidationError, RunConfig
from doctor.core.pipeline import Pipeline
from doctor.core.registry import BACKEND_NAMES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doctor",
        description="Local LLM Performance Doctor",
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

    parser.error(f"Unknown command: {args.command}")
    return 2
