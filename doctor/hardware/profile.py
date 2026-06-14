from __future__ import annotations

import csv
import json
import platform
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from doctor.collectors.nvidia import find_nvidia_smi, to_float


SCHEMA_VERSION = "0.1"
CUDA_VERSION_RE = re.compile(r"CUDA Version:\s*([\d.]+)")


@dataclass(frozen=True)
class GpuInfo:
    name: str
    vram_total_mb: float | None
    driver_version: str | None


@dataclass(frozen=True)
class HardwareProfile:
    schema_version: str
    created_at: str
    os_name: str
    os_release: str
    os_version: str
    python_version: str
    cpu_name: str | None
    cpu_physical_cores: int | None
    cpu_logical_cores: int | None
    ram_total_gb: float | None
    gpus: list[GpuInfo] = field(default_factory=list)
    cuda_available: bool = False
    cuda_version: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def primary_gpu(self) -> GpuInfo | None:
        return self.gpus[0] if self.gpus else None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_hardware_profile() -> HardwareProfile:
    notes: list[str] = []
    physical, logical, ram_gb = _system_resources(notes)
    gpus, cuda_version = _collect_gpus(notes)

    return HardwareProfile(
        schema_version=SCHEMA_VERSION,
        created_at=datetime.now().isoformat(timespec="seconds"),
        os_name=platform.system() or "unknown",
        os_release=platform.release() or "",
        os_version=platform.version() or "",
        python_version=platform.python_version(),
        cpu_name=_cpu_name(),
        cpu_physical_cores=physical,
        cpu_logical_cores=logical,
        ram_total_gb=ram_gb,
        gpus=gpus,
        cuda_available=bool(gpus),
        cuda_version=cuda_version,
        notes=notes,
    )


def save_profile(profile: HardwareProfile, path: Path | str) -> Path:
    path = Path(path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(profile.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _system_resources(notes: list[str]) -> tuple[int | None, int | None, float | None]:
    try:
        import psutil
    except ImportError:
        notes.append("psutil is not installed; CPU core counts and RAM total are unavailable.")
        return None, None, None

    ram_gb = round(psutil.virtual_memory().total / (1024**3), 2)
    return psutil.cpu_count(logical=False), psutil.cpu_count(logical=True), ram_gb


def _collect_gpus(notes: list[str]) -> tuple[list[GpuInfo], str | None]:
    nvidia_smi = find_nvidia_smi()
    if nvidia_smi is None:
        notes.append("nvidia-smi was not found; GPU, VRAM, and CUDA details are unavailable.")
        return [], None

    try:
        result = subprocess.run(
            [
                str(nvidia_smi),
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
        )
    except Exception as exc:
        notes.append(f"nvidia-smi query failed: {exc}")
        return [], None

    if result.returncode != 0:
        notes.append((result.stderr or result.stdout or "nvidia-smi failed").strip())
        return [], None

    gpus: list[GpuInfo] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = next(csv.reader([line], skipinitialspace=True))
        if len(parts) < 2 or not parts[0].strip():
            continue
        driver = parts[2].strip() if len(parts) > 2 else ""
        gpus.append(
            GpuInfo(
                name=parts[0].strip(),
                vram_total_mb=to_float(parts[1]),
                driver_version=driver or None,
            )
        )

    if not gpus:
        notes.append("nvidia-smi returned no GPU rows.")
        return [], None

    return gpus, _cuda_version(nvidia_smi)


def _cuda_version(nvidia_smi: Path) -> str | None:
    try:
        result = subprocess.run(
            [str(nvidia_smi)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
        )
    except Exception:
        return None

    if result.returncode != 0:
        return None

    match = CUDA_VERSION_RE.search(result.stdout)
    return match.group(1) if match else None


def _cpu_name() -> str | None:
    system = platform.system()
    if system == "Windows":
        name = _windows_cpu_name()
    elif system == "Linux":
        name = _linux_cpu_name()
    elif system == "Darwin":
        name = _macos_cpu_name()
    else:
        name = None

    if name:
        return name

    fallback = platform.processor() or platform.machine()
    return fallback or None


def _windows_cpu_name() -> str | None:
    try:
        import winreg
    except ImportError:
        return None

    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        )
        try:
            value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        finally:
            winreg.CloseKey(key)
    except OSError:
        return None

    return str(value).strip() or None


def _linux_cpu_name() -> str | None:
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as cpuinfo:
            for line in cpuinfo:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip() or None
    except OSError:
        return None
    return None


def _macos_cpu_name() -> str | None:
    try:
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return None

    if result.returncode != 0:
        return None
    return result.stdout.strip() or None
