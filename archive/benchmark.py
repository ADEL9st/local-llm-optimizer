import argparse
import json
import subprocess
import time


def run_ollama_benchmark(model: str, prompt: str):
    print(f"Running Ollama benchmark with model: {model}")

    start_time = time.time()

    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except FileNotFoundError:
        print("ERROR: Ollama bulunamadı. Terminalde 'ollama --version' çalışıyor mu kontrol et.")
        return
    except subprocess.TimeoutExpired:
        print("ERROR: Benchmark timeout oldu.")
        return

    end_time = time.time()
    duration = end_time - start_time

    output = result.stdout.strip()
    error = result.stderr.strip()

    if error:
        print("\n--- STDERR ---")
        print(error)

    words = len(output.split())
    chars = len(output)

    print("\n=== LLM Benchmark Result ===")
    print(f"Model: {model}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Output words: {words}")
    print(f"Output chars: {chars}")

    if duration > 0:
        print(f"Approx words/sec: {words / duration:.2f}")
        print(f"Approx chars/sec: {chars / duration:.2f}")

    print("\n=== Model Output Preview ===")
    print(output[:1000])


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--backend",
        type=str,
        default="ollama",
        choices=["ollama"],
        help="Benchmark backend",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="llama3.2:3b",
        help="Ollama model name",
    )

    parser.add_argument(
        "--prompt",
        type=str,
        default="Explain what a Verilog module is in 5 bullet points.",
        help="Prompt to send to the model",
    )

    args = parser.parse_args()

    if args.backend == "ollama":
        run_ollama_benchmark(args.model, args.prompt)


if __name__ == "__main__":
    main()