import time
import math
import argparse


def cpu_benchmark(duration_seconds: int):
    print(f"CPU benchmark başladı. Süre: {duration_seconds} saniye")

    start = time.time()
    operations = 0

    while time.time() - start < duration_seconds:
        for i in range(1, 10000):
            math.sqrt(i) * math.sin(i) * math.cos(i)
            operations += 1

    print("CPU benchmark bitti.")
    print(f"Yaklaşık operasyon sayısı: {operations}")


def memory_benchmark(duration_seconds: int, size_mb: int):
    print(f"RAM benchmark başladı. Ayrılacak bellek: {size_mb} MB")

    block = bytearray(size_mb * 1024 * 1024)

    start = time.time()
    step = 4096

    while time.time() - start < duration_seconds:
        for i in range(0, len(block), step):
            block[i] = (block[i] + 1) % 256

    print("RAM benchmark bitti.")


def mixed_benchmark(duration_seconds: int, size_mb: int):
    print("Mixed benchmark başladı.")

    start = time.time()
    block = bytearray(size_mb * 1024 * 1024)
    operations = 0

    while time.time() - start < duration_seconds:
        for i in range(1, 5000):
            math.sqrt(i) * math.sin(i)
            operations += 1

        for i in range(0, len(block), 4096 * 64):
            block[i] = (block[i] + 1) % 256

    print("Mixed benchmark bitti.")
    print(f"Yaklaşık operasyon sayısı: {operations}")


def main():
    parser = argparse.ArgumentParser(description="Simple local performance benchmark")

    parser.add_argument(
        "--mode",
        choices=["cpu", "memory", "mixed"],
        default="mixed",
        help="Benchmark modu",
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Benchmark süresi saniye cinsinden",
    )

    parser.add_argument(
        "--memory-mb",
        type=int,
        default=512,
        help="RAM benchmark için ayrılacak bellek miktarı",
    )

    args = parser.parse_args()

    if args.mode == "cpu":
        cpu_benchmark(args.duration)
    elif args.mode == "memory":
        memory