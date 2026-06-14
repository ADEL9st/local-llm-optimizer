from __future__ import annotations

import json

from doctor.core.config import load_locale
from doctor.hardware import (
    GpuInfo,
    HardwareProfile,
    collect_hardware_profile,
    save_profile,
)
from doctor.hardware.reporter import HardwareReporter

EN = load_locale("en")
TR = load_locale("tr")


def _profile(**overrides) -> HardwareProfile:
    base = dict(
        schema_version="0.1",
        created_at="2026-06-12T00:00:00",
        os_name="Windows",
        os_release="10",
        os_version="10.0.19045",
        python_version="3.11.9",
        cpu_name="Intel Core i5-10400",
        cpu_physical_cores=6,
        cpu_logical_cores=12,
        ram_total_gb=32.0,
        gpus=[GpuInfo(name="NVIDIA GeForce GTX 1660", vram_total_mb=6144.0, driver_version="576.88")],
        cuda_available=True,
        cuda_version="12.9",
        notes=[],
    )
    base.update(overrides)
    return HardwareProfile(**base)


def test_collect_returns_profile_with_runtime_basics():
    profile = collect_hardware_profile()

    assert isinstance(profile, HardwareProfile)
    assert profile.schema_version == "0.1"
    assert profile.python_version  # always available
    assert profile.os_name  # platform.system() is never empty in practice
    assert isinstance(profile.gpus, list)
    assert isinstance(profile.notes, list)


def test_to_dict_serializes_nested_gpus():
    data = _profile().to_dict()

    assert data["gpus"][0]["name"] == "NVIDIA GeForce GTX 1660"
    assert data["gpus"][0]["vram_total_mb"] == 6144.0
    # round-trips through JSON without custom encoders
    assert json.loads(json.dumps(data))["cuda_version"] == "12.9"


def test_save_profile_writes_valid_json(tmp_path):
    path = save_profile(_profile(), tmp_path / "nested" / "hardware.json")

    assert path.is_file()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["os_name"] == "Windows"
    assert loaded["cpu_physical_cores"] == 6


def test_reporter_renders_core_fields():
    text = HardwareReporter(EN).render(_profile())

    assert "Hardware Profile" in text
    assert "Windows 10" in text
    assert "6 cores / 12 threads" in text
    assert "32 GB" in text
    assert "NVIDIA GeForce GTX 1660" in text
    assert "6 GB" in text
    assert "available (12.9)" in text
    assert "576.88" in text


def test_reporter_handles_no_gpu_and_notes():
    profile = _profile(
        gpus=[],
        cuda_available=False,
        cuda_version=None,
        ram_total_gb=None,
        cpu_physical_cores=None,
        cpu_logical_cores=None,
        notes=["nvidia-smi was not found; GPU, VRAM, and CUDA details are unavailable."],
    )
    text = HardwareReporter(EN).render(profile)

    assert "none detected" in text
    assert "not available" in text
    assert "unknown" in text  # RAM unknown
    assert "Notes" in text
    assert "nvidia-smi" in text


def test_reporter_uses_turkish_labels():
    text = HardwareReporter(TR).render(_profile())

    assert "Donanım Profili" in text
    assert "İşletim Sistemi" in text
    assert "Ekran Kartı" in text
    assert "mevcut" in text
