import csv
import os
import time
from datetime import datetime

import psutil


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "metrics.csv")


def get_cpu_ram_metrics():
    cpu_percent = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()

    return {
        "cpu_percent": cpu_percent,
        "ram_percent": ram.percent,
        "ram_used_gb": round(ram.used / (1024 ** 3), 2),
        "ram_total_gb": round(ram.total / (1024 ** 3), 2),
    }


def get_gpu_metrics():
    """
    NVIDIA GPU varsa nvidia-smi üzerinden ölçüm alır.
    GPU yoksa None döndürür.
    """
    try:
        import subprocess

        result = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits",
            ],
            encoding="utf-8",
        )

        first_gpu = result.strip().split("\n")[0]
        gpu_util, vram_used, vram_total, temp, power = [
            x.strip() for x in first_gpu.split(",")
        ]

        return {
            "gpu_util_percent": float(gpu_util),
            "vram_used_mb": float(vram_used),
            "vram_total_mb": float(vram_total),
            "gpu_temp_c": float(temp),
            "gpu_power_w": float(power),
        }

    except Exception:
        return {
            "gpu_util_percent": None,
            "vram_used_mb": None,
            "vram_total_mb": None,
            "gpu_temp_c": None,
            "gpu_power_w": None,
        }


def init_log_file():
    os.makedirs(LOG_DIR, exist_ok=True)

    file_exists = os.path.exists(LOG_FILE)

    fieldnames = [
        "timestamp",
        "cpu_percent",
        "ram_percent",
        "ram_used_gb",
        "ram_total_gb",
        "gpu_util_percent",
        "vram_used_mb",
        "vram_total_mb",
        "gpu_temp_c",
        "gpu_power_w",
    ]

    if not file_exists:
        with open(LOG_FILE, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    return fieldnames


def append_metrics(fieldnames):
    cpu_ram = get_cpu_ram_metrics()
    gpu = get_gpu_metrics()

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        **cpu_ram,
        **gpu,
    }

    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)

    return row


def main():
    fieldnames = init_log_file()

    print("Local monitoring started.")
    print(f"Writing metrics to: {LOG_FILE}")
    print("Press CTRL+C to stop.\n")

    try:
        while True:
            row = append_metrics(fieldnames)

            print(
                f"[{row['timestamp']}] "
                f"CPU: {row['cpu_percent']}% | "
                f"RAM: {row['ram_percent']}% | "
                f"GPU: {row['gpu_util_percent']}% | "
                f"VRAM: {row['vram_used_mb']}/{row['vram_total_mb']} MB"
            )

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


if __name__ == "__main__":
    main()