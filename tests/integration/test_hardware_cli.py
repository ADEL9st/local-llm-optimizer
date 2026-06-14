from __future__ import annotations

import json
from pathlib import Path

from doctor.cli import main


def test_hardware_cli_writes_profile_and_renders(tmp_path, capsys):
    output = tmp_path / "hardware.json"

    exit_code = main(["hardware", "--lang", "en", "--output", str(output)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Hardware Profile" in out
    assert output.is_file()

    data = json.loads(output.read_text(encoding="utf-8"))
    for key in ("schema_version", "os_name", "python_version", "gpus", "cuda_available", "notes"):
        assert key in data


def test_hardware_cli_creates_missing_parent_dir(tmp_path):
    output = tmp_path / "deep" / "dir" / "hardware.json"

    exit_code = main(["hardware", "--lang", "tr", "--output", str(output)])

    assert exit_code == 0
    assert output.is_file()
