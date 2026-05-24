import csv
import os
from statistics import mean


LOG_FILE = os.path.join("logs", "metrics.csv")


def to_float(value):
    if value is None:
        return None

    value = str(value).strip()

    if value == "" or value.lower() == "none":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def load_metrics():
    if not os.path.exists(LOG_FILE):
        raise FileNotFoundError(f"Log file not found: {LOG_FILE}")

    rows = []

    with open(LOG_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append({
                "timestamp": row.get("timestamp"),
                "cpu_percent": to_float(row.get("cpu_percent")),
                "ram_percent": to_float(row.get("ram_percent")),
                "ram_used_gb": to_float(row.get("ram_used_gb")),
                "ram_total_gb": to_float(row.get("ram_total_gb")),
                "gpu_util_percent": to_float(row.get("gpu_util_percent")),
                "vram_used_mb": to_float(row.get("vram_used_mb")),
                "vram_total_mb": to_float(row.get("vram_total_mb")),
                "gpu_temp_c": to_float(row.get("gpu_temp_c")),
                "gpu_power_w": to_float(row.get("gpu_power_w")),
            })

    return rows


def clean_values(rows, key):
    return [row[key] for row in rows if row.get(key) is not None]


def summarize_metric(rows, key):
    values = clean_values(rows, key)

    if not values:
        return None

    return {
        "avg": round(mean(values), 2),
        "max": round(max(values), 2),
        "min": round(min(values), 2),
    }


def print_summary(name, summary, unit="%"):
    if summary is None:
        print(f"{name}: veri yok")
        return

    print(
        f"{name}: avg={summary['avg']}{unit} | "
        f"max={summary['max']}{unit} | "
        f"min={summary['min']}{unit}"
    )


def analyze_cpu(cpu_summary):
    if cpu_summary is None:
        return "CPU verisi yok."

    avg_cpu = cpu_summary["avg"]
    max_cpu = cpu_summary["max"]

    if avg_cpu >= 85:
        return "CPU darboğazı güçlü ihtimal. CPU sürekli yüksek çalışmış."
    elif max_cpu >= 90 and avg_cpu >= 60:
        return "CPU zaman zaman darboğaz olmuş olabilir."
    elif avg_cpu < 40:
        return "CPU genel olarak rahat. Ana darboğaz CPU gibi görünmüyor."
    else:
        return "CPU kullanımı orta seviyede. Net darboğaz görünmüyor."


def analyze_ram(ram_summary):
    if ram_summary is None:
        return "RAM verisi yok."

    avg_ram = ram_summary["avg"]
    max_ram = ram_summary["max"]

    if max_ram >= 90:
        return "RAM baskısı yüksek. Sistem swap/pagefile kullanmaya başlamış olabilir."
    elif avg_ram >= 75:
        return "RAM kullanımı yüksek. Daha büyük model veya batch için riskli."
    elif avg_ram < 50:
        return "RAM rahat görünüyor."
    else:
        return "RAM kullanımı normal/orta seviyede."


def analyze_gpu(gpu_summary):
    if gpu_summary is None:
        return "GPU verisi yok. nvidia-smi çalışmıyor olabilir veya NVIDIA GPU yok."

    avg_gpu = gpu_summary["avg"]
    max_gpu = gpu_summary["max"]

    if avg_gpu < 20 and max_gpu < 50:
        return "GPU düşük kullanılmış. İş yükü GPU'ya yeterince gitmiyor olabilir."
    elif avg_gpu >= 80:
        return "GPU iyi kullanılmış. Ana yük GPU üzerinde."
    elif max_gpu >= 80 and avg_gpu < 50:
        return "GPU kısa patlamalarla kullanılmış. Veri besleme veya CPU tarafı yavaş olabilir."
    else:
        return "GPU kullanımı orta seviyede."


def analyze_vram(vram_used_summary, vram_total_values):
    if vram_used_summary is None or not vram_total_values:
        return "VRAM verisi yok."

    max_used = vram_used_summary["max"]
    total = max(vram_total_values)

    if total <= 0:
        return "VRAM toplam değeri okunamadı."

    ratio = max_used / total * 100

    if ratio >= 90:
        return f"VRAM neredeyse dolmuş. Maksimum kullanım %{ratio:.1f}. OOM riski yüksek."
    elif ratio >= 75:
        return f"VRAM kullanımı yüksek. Maksimum kullanım %{ratio:.1f}."
    elif ratio < 40:
        return f"VRAM rahat. Maksimum kullanım %{ratio:.1f}."
    else:
        return f"VRAM kullanımı orta seviyede. Maksimum kullanım %{ratio:.1f}."


def make_recommendations(cpu_summary, ram_summary, gpu_summary, vram_used_summary, vram_total_values):
    recommendations = []

    if cpu_summary and cpu_summary["avg"] >= 85:
        recommendations.append("- CPU yüksek: worker sayısını azalt, arka plan uygulamalarını kapat veya daha GPU ağırlıklı inference kullan.")

    if ram_summary and ram_summary["max"] >= 90:
        recommendations.append("- RAM çok yüksek: daha küçük model, daha düşük context length veya quantized model kullan.")

    if gpu_summary and gpu_summary["avg"] < 20:
        recommendations.append("- GPU düşük: model CPU'da çalışıyor olabilir; CUDA/torch GPU kurulumunu ve inference backend ayarlarını kontrol et.")

    if vram_used_summary and vram_total_values:
        max_used = vram_used_summary["max"]
        total = max(vram_total_values)

        if total > 0:
            ratio = max_used / total * 100

            if ratio >= 90:
                recommendations.append("- VRAM sınırda: batch size/context azalt, 4-bit quantization kullan veya daha küçük model seç.")
            elif ratio < 40:
                recommendations.append("- VRAM boş kalmış: model gerçekten GPU'ya yükleniyor mu kontrol et; daha büyük batch/context denenebilir.")

    if not recommendations:
        recommendations.append("- Şu an net bir kritik darboğaz görünmüyor. Daha gerçekçi LLM benchmark testi eklenmeli.")

    return recommendations


def main():
    rows = load_metrics()

    if not rows:
        print("CSV boş. Önce monitor.py çalıştırıp veri toplamalısın.")
        return

    cpu_summary = summarize_metric(rows, "cpu_percent")
    ram_summary = summarize_metric(rows, "ram_percent")
    gpu_summary = summarize_metric(rows, "gpu_util_percent")
    vram_used_summary = summarize_metric(rows, "vram_used_mb")
    vram_total_values = clean_values(rows, "vram_total_mb")

    print("\n=== Local LLM Performance Doctor Report ===\n")
    print(f"Analiz edilen örnek sayısı: {len(rows)}\n")

    print("=== Özet Metrikler ===")
    print_summary("CPU", cpu_summary, "%")
    print_summary("RAM", ram_summary, "%")
    print_summary("GPU", gpu_summary, "%")
    print_summary("VRAM Used", vram_used_summary, " MB")

    print("\n=== Yorum ===")
    print(f"CPU: {analyze_cpu(cpu_summary)}")
    print(f"RAM: {analyze_ram(ram_summary)}")
    print(f"GPU: {analyze_gpu(gpu_summary)}")
    print(f"VRAM: {analyze_vram(vram_used_summary, vram_total_values)}")

    print("\n=== Öneriler ===")
    for recommendation in make_recommendations(
        cpu_summary,
        ram_summary,
        gpu_summary,
        vram_used_summary,
        vram_total_values,
    ):
        print(recommendation)


if __name__ == "__main__":
    main()