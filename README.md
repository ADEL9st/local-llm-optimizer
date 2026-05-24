# Local LLM Performance Doctor

Local LLM Performance Doctor benchmarks local LLM runs, captures CPU/RAM/GPU/VRAM metrics, and explains bottlenecks with diagnosis and advisor reports.

v0.2.0 adds a rule-grounded Advisor Agent.

The agent explains diagnosis results and gives prioritized recommendations.
It does not modify system settings.

v0.2.0 kural-tabanlı Advisor Agent ekler.

Agent teşhis sonuçlarını açıklar ve öncelikli öneriler verir.
Sistem ayarlarını değiştirmez.

## Kurulum

```powershell
pip install -e .
```

Geliştirme ve test için:

```powershell
pip install -e ".[dev]"
```

## Kullanım

Ollama:

```powershell
doctor run --backend ollama --model llama3:latest --lang tr --prompt "Local LLM performansı nasıl ölçülür? 8 maddede açıkla."
```

LM Studio:

```powershell
doctor run --backend lmstudio --model "model-id" --lang tr --max-tokens 512
```

OpenAI-compatible:

```powershell
doctor run --backend openai-compatible --base-url http://localhost:1234/v1 --model "model-id" --lang tr
```

## Advisor Config

`run.json` içinde advisor ayarı nested olarak saklanır:

```yaml
advisor:
  enabled: true
  mode: deterministic
  language: tr
```

## Testler

Tüm testleri çalıştır:

```powershell
python -m pytest
```

Sessiz çıktı için:

```powershell
python -m pytest -q
```

## Çıktılar

Her koşu `runs/` altında zaman damgalı bir klasör üretir:

- `run.json`
- `metrics.csv`
- `report.md`

## Sample Run Output

```text
=== Local LLM Performance Doctor Raporu ===
Model: mock-model
Backend: ollama
Süre: 0.25s
Örnek sayısı: 1
Durum: Başarılı

--- Teşhisler ---
[WARNING] GPU düşük kullanımda görünüyor
  GPU ortalaması ve zirvesi düşük. Model CPU'da çalışıyor veya iş yükü GPU'ya gitmiyor olabilir.

--- Advisor Agent ---
En önemli sorun: GPU kullanılmıyor olabilir.
Bu koşu, inference sırasında modelin GPU yoluna tam olarak ulaşmadığını düşündürüyor.
Kanıt:
- Ortalama GPU kullanımı %4.0.
- Tepe VRAM kullanımı mevcut VRAM'in sadece %4.2 seviyesinde kaldı.
Öncelikli Öneriler:
1. Ollama / LM Studio GPU acceleration ayarını kontrol et.
2. NVIDIA driver / CUDA durumunu kontrol et.
3. Aynı benchmark'ı GPU aktifken tekrar çalıştır.
```

## v0.2.0 - Advisor Agent MVP

- Added rule-grounded Advisor Agent
- Added prioritized recommendations
- Added TR/EN advisor output
- Integrated advisor output into terminal/markdown reports
- Advisor does not modify runtime/system settings

## Önceki Sürüm Notları

### v0.1.2

- LM Studio `base_url` handling düzeltildi; `/v1` eksikse otomatik tamamlanır.
- README örnekleri netleştirildi.
- Sample run output eklendi.

### v0.1.1

- Windows NVIDIA collector daha dayanıklı hale getirildi.
- Ollama çalışmıyorken daha anlaşılır hata mesajları eklendi.
- Markdown rapor formatı iyileştirildi.
