
import json
import subprocess
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


def test_rejected_command_never_reaches_subprocess(monkeypatch):
    def unexpected_execution(*args, **kwargs):
        raise AssertionError("Unapproved command reached subprocess")

    monkeypatch.setattr(
        inspector.subprocess,
        "run",
        unexpected_execution
    )

    result = inspector.run_command(["whoami"])

    assert result["error"] == "Command is not allow-listed"


def test_run_command_uses_safe_subprocess_options(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        inspector.shutil,
        "which",
        lambda command: "/usr/bin/lscpu"
    )

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs

        return SimpleNamespace(
            returncode=0,
            stdout="CPU information",
            stderr=""
        )

    monkeypatch.setattr(
        inspector.subprocess,
        "run",
        fake_run
    )

    result = inspector.run_command(["lscpu"])

    assert result == {"output": "CPU information"}
    assert captured["command"] == ["/usr/bin/lscpu"]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["timeout"] == 10
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["text"] is True


def test_command_timeout_is_handled(monkeypatch):
    monkeypatch.setattr(
        inspector.shutil,
        "which",
        lambda command: "/usr/bin/lscpu"
    )

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd="lscpu",
            timeout=10
        )

    monkeypatch.setattr(
        inspector.subprocess,
        "run",
        fake_run
    )

    result = inspector.run_command(["lscpu"])

    assert result["error"] == "Command execution timed out"


def test_command_os_error_is_handled(monkeypatch):
    monkeypatch.setattr(
        inspector.shutil,
        "which",
        lambda command: "/usr/bin/lscpu"
    )

    def fake_run(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(
        inspector.subprocess,
        "run",
        fake_run
    )

    result = inspector.run_command(["lscpu"])

    assert result["error"] == "Unable to execute command"
    assert "Permission denied" not in result["details"]


def test_cpu_information(monkeypatch):
    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {"output": "Model name: Test Intel CPU\n"}
    )
    monkeypatch.setattr(
        inspector.psutil,
        "cpu_count",
        lambda logical: 4 if logical else 2
    )

    result = inspector.get_cpu_info()

    assert result["model"] == "Test Intel CPU"
    assert result["physical_cores"] == 2
    assert result["logical_processors"] == 4
    assert "scope" in result


def test_cpu_model_alternative_field(monkeypatch):
    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {"output": "Model: Test CPU\n"}
    )

    result = inspector.get_cpu_info()

    assert result["model"] == "Test CPU"


def test_memory_information(monkeypatch):
    fake_memory = SimpleNamespace(
        total=8 * (1024 ** 3),
        available=4 * (1024 ** 3),
        used=4 * (1024 ** 3),
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
    assert result["used_gb"] == 4
    assert result["used_percent"] == 50
    assert "scope" in result


def test_storage_information(monkeypatch):
    storage_data = {
        "blockdevices": [
            {
                "name": "sda",
                "size": "100G",
                "type": "disk",
                "mountpoint": "/home/private-user"
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
    assert "mountpoint" not in result[0]
    assert "/home/private-user" not in json.dumps(result)


def test_storage_partitions_exclude_mount_points(monkeypatch):
    storage_data = {
        "blockdevices": [
            {
                "name": "sda",
                "size": "100G",
                "type": "disk",
                "mountpoint": "/",
                "children": [
                    {
                        "name": "sda1",
                        "size": "100G",
                        "type": "part",
                        "mountpoint": "/home/private-user"
                    }
                ]
            }
        ]
    }

    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {"output": json.dumps(storage_data)}
    )

    result = inspector.get_storage_info()

    serialized = json.dumps(result)

    assert "mountpoint" not in serialized
    assert "/home/private-user" not in serialized
    assert result[0]["partitions"][0]["name"] == "sda1"


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


def test_memory_slots_parse_successfully(monkeypatch):
    output = """
Handle 0x0010, DMI type 16
Physical Memory Array
    Maximum Capacity: 32 GB
    Number Of Devices: 2

Handle 0x0011, DMI type 17
Memory Device
    Size: 8192 MB
    Locator: DIMM A
    Type: DDR4
    Speed: 2400 MT/s
    Configured Memory Speed: 2133 MT/s

Handle 0x0012, DMI type 17
Memory Device
    Size: No Module Installed
    Locator: DIMM B
    Type: Unknown
"""

    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {"output": output}
    )

    result = inspector.get_memory_slot_info()

    assert result["status"] == "Retrieved"
    assert result["total_slots"] == 2
    assert result["installed_slots"] == 1
    assert result["free_slots"] == 1
    assert result["maximum_capacity_gb"] == 32
    assert result["modules"][0]["size"] == "8192 MB"
    assert result["modules"][1]["installed"] is False


def test_memory_slot_output_excludes_serial_numbers(monkeypatch):
    output = """
Physical Memory Array
    Maximum Capacity: 32 GB
    Number Of Devices: 1

Memory Device
    Size: 8192 MB
    Locator: DIMM A
    Type: DDR4
    Speed: 2400 MT/s
    Serial Number: PRIVATE-SERIAL-123
"""

    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {"output": output}
    )

    result = inspector.get_memory_slot_info()

    serialized = json.dumps(result)

    assert "PRIVATE-SERIAL-123" not in serialized
    assert result["installed_slots"] == 1


def test_memory_slots_missing_smbios(monkeypatch):
    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {
            "output": "No SMBIOS nor DMI entry point found"
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


def test_detects_nvme_storage(monkeypatch):
    storage_data = {
        "blockdevices": [
            {
                "name": "nvme0n1",
                "size": "512G",
                "type": "disk",
                "rota": "0",
                "model": "Test NVMe"
            }
        ]
    }

    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {"output": json.dumps(storage_data)}
    )

    result = inspector.get_storage_info()

    assert result[0]["storage_kind"] == "SSD"
    assert result[0]["interface"] == "NVMe"


def test_detects_rotational_hdd(monkeypatch):
    storage_data = {
        "blockdevices": [
            {
                "name": "sda",
                "size": "1T",
                "type": "disk",
                "rota": "1",
                "model": "Test HDD"
            }
        ]
    }

    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {"output": json.dumps(storage_data)}
    )

    result = inspector.get_storage_info()

    assert result[0]["storage_kind"] == "HDD"


def test_detects_non_rotational_storage(monkeypatch):
    storage_data = {
        "blockdevices": [
            {
                "name": "sda",
                "size": "256G",
                "type": "disk",
                "rota": "0",
                "model": "Test SSD"
            }
        ]
    }

    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {"output": json.dumps(storage_data)}
    )

    result = inspector.get_storage_info()

    assert result[0]["storage_kind"] == "SSD"
    assert result[0]["interface"] == "Unknown"


def test_virtual_disk_not_misclassified_as_hdd(monkeypatch):
    storage_data = {
        "blockdevices": [
            {
                "name": "sda",
                "size": "1T",
                "type": "disk",
                "rota": "1",
                "model": "Virtual Disk"
            }
        ]
    }

    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {"output": json.dumps(storage_data)}
    )

    result = inspector.get_storage_info()

    assert result[0]["storage_kind"] == "Virtual disk"
    assert result[0]["interface"] == "Unknown"


def test_missing_gpu_utility(monkeypatch):
    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {
            "error": "Required utility is not installed",
            "details": "lspci"
        }
    )

    result = inspector.get_gpu_info()

    assert result["status"] == "Unavailable"
    assert result["reason"] == "lspci"


def test_missing_storage_utility(monkeypatch):
    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {
            "error": "Required utility is not installed",
            "details": "lsblk"
        }
    )

    result = inspector.get_storage_info()

    assert result["status"] == "Unavailable"
    assert result["reason"] == "lsblk"


def test_missing_cpu_utility(monkeypatch):
    monkeypatch.setattr(
        inspector,
        "run_command",
        lambda command: {
            "error": "Required utility is not installed",
            "details": "lscpu"
        }
    )

    monkeypatch.setattr(
        inspector.psutil,
        "cpu_count",
        lambda logical: 4 if logical else 2
    )

    result = inspector.get_cpu_info()

    assert result["model"] == "Unavailable"
    assert result["physical_cores"] == 2
    assert result["logical_processors"] == 4
    assert result["status"] == "Required utility is not installed"


def test_os_information():
    result = inspector.get_os_info()

    assert "system" in result
    assert "distribution" in result
    assert "kernel" in result
    assert "architecture" in result
    assert isinstance(result["is_wsl"], bool)
