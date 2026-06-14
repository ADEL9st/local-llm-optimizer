import time
import math
import argparse
import multiprocessing as mp


def cpu_worker(duration_seconds: int):
    end_time = time.time() + duration_seconds
    x = 0.0

    while time.time() < end_time:
        for i in range(1, 50_000):
            x += math.sqrt(i) * math.sin(i)

    return x


def ram_load(size_mb: int):
    """
    Basit RAM yükü oluşturur.
    size_mb kadar yaklaşık bellek ayırır.
    """
    if size_mb <= 0:
        return None

    print(f"Allocating about {size_mb} MB RAM...")
    block = bytearray(size_mb * 1024 * 1024)

    # RAM gerçekten kullanılsın
    for i in range(0, len(block), 4096):
        block[i] = 1

    return block


def run_cpu_benchmark(duration_seconds: int, workers: int):
    print(f"CPU benchmark started: {duration_seconds}s, workers={workers}")

    with mp.Pool(processes=workers) as pool:
        results = [
            pool.apply_async(cpu_worker, args=(duration_seconds,))
            for _ in range(workers)
        ]

        for r in results:
            r.get()

    print("CPU benchmark finished.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 1))
    parser.add_argument("--ram-mb", type=int, default=512)

    args = parser.parse_args()

    ram_block = ram_load(args.ram_mb)

    run_cpu_benchmark(
        duration_seconds=args.duration,
        workers=args.workers,
    )

    # RAM hemen silinmesin bekletiyoruz
    if ram_block is not None:
        print("Keeping RAM allocated for 5 seconds...")
        time.sleep(5)

    print("Benchmark done.")


if __name__ == "__main__":
    main()