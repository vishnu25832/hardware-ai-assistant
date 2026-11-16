import json
from types import SimpleNamespace

from hardware import inspector


def test_rejects_unapproved_command():
    result = inspector.run_command(["whoami"])
    assert result["error"] == "Command is not allow-listed"


def test_rejects_invalid_command_format():
    result = inspector.run_command("lscpu")
    assert result["error"] == "Invalid command format"


def test_rejects_command_injection():
    result = inspector.run_command(["lscpu", "&&", "whoami"])
    assert result["error"] == "Command is not allow-listed"


def test_cpu_information(monkeypatch):
    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {
            "output": "Model name: Test Intel CPU\n"
        }
    )

    monkeypatch.setattr(inspector.psutil, "cpu_count",
                        lambda logical: 4 if logical else 2)

    result = inspector.get_cpu_info()

    assert result["model"] == "Test Intel CPU"
    assert result["physical_cores"] == 2
    assert result["logical_processors"] == 4


def test_memory_information(monkeypatch):
    fake_memory = SimpleNamespace(
        total=8 * (1024 ** 3),
        available=4 * (1024 ** 3),
        percent=50
    )

    monkeypatch.setattr(
        inspector.psutil,
        "virtual_memory",
        lambda: fake_memory
    )

    result = inspector.get_memory_info()

    assert result["total_gb"] == 8
    assert result["available_gb"] == 4
    assert result["used_percent"] == 50


def test_storage_information(monkeypatch):
    storage_data = {
        "blockdevices": [
            {
                "name": "sda",
                "size": "100G",
                "type": "disk"
            }
        ]
    }

    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {"output": json.dumps(storage_data)}
    )

    result = inspector.get_storage_info()

    assert len(result) == 1
    assert result[0]["name"] == "sda"


def test_memory_slots_unavailable(monkeypatch):
    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {
            "error": "Command failed",
            "details": "Can't read memory from /dev/mem"
        }
    )

    result = inspector.get_memory_slot_info()

    assert result["status"] == "Unavailable"


def test_gpu_information(monkeypatch):
    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {
            "output": (
                "00:02.0 VGA compatible controller: "
                "Microsoft Basic Render Driver\n"
            )
        }
    )

    result = inspector.get_gpu_info()

    assert len(result) == 1
    assert "VGA compatible controller" in result[0]
