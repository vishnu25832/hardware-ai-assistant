
import json
import platform
import shutil
import subprocess

import psutil


ALLOWED_COMMANDS = {
    ("lscpu",),
    ("lspci",),
    (
        "lsblk",
        "-J",
        "-o",
        "NAME,SIZE,TYPE,ROTA,MODEL,FSTYPE,MOUNTPOINT"
    ),
    ("dmidecode", "-t", "memory"),
}


def run_command(command):
    """Execute only explicitly approved read-only commands."""

    if not isinstance(command, (list, tuple)):
        return {"error": "Invalid command format"}

    command = tuple(command)

    if command not in ALLOWED_COMMANDS:
        return {"error": "Command is not allow-listed"}

    executable = shutil.which(command[0])

    if not executable:
        return {"error": f"{command[0]} is not installed"}

    try:
        result = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            shell=False
        )

        if result.returncode != 0:
            return {
                "error": "Command failed",
                "details": result.stderr.strip()
            }

        return {"output": result.stdout}

    except subprocess.TimeoutExpired:
        return {"error": "Command execution timed out"}

    except OSError as error:
        return {
            "error": "Unable to execute command",
            "details": str(error)
        }


def get_cpu_info():
    result = run_command(["lscpu"])

    info = {
        "architecture": platform.machine(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_processors": psutil.cpu_count(logical=True),
        "model": "Unavailable"
    }

    if "output" not in result:
        info["status"] = result["error"]
        return info

    for line in result["output"].splitlines():
        if line.startswith("Model name:"):
            info["model"] = line.split(":", 1)[1].strip()
            break

    return info


def get_memory_info():
    try:
        memory = psutil.virtual_memory()

        return {
            "total_gb": round(memory.total / (1024 ** 3), 2),
            "available_gb": round(memory.available / (1024 ** 3), 2),
            "used_percent": memory.percent
        }

    except Exception:
        return {"status": "Memory information unavailable"}


def get_memory_slot_info():
    """Attempt optional BIOS memory-slot inspection."""

    result = run_command(["dmidecode", "-t", "memory"])

    if "output" not in result:
        return {
            "status": "Unavailable",
            "reason": result.get("details", result.get("error")),
            "note": (
                "SMBIOS access may require elevated permissions "
                "or may be unavailable in virtualized environments."
            )
        }

    output = result["output"]

    if "No SMBIOS nor DMI entry point found" in output:
        return {
            "status": "Unavailable",
            "reason": "SMBIOS/DMI information is not exposed"
        }

    return {
        "status": "Retrieved",
        "raw_output": output
    }


def get_storage_info():
    result = run_command([
        "lsblk",
        "-J",
        "-o",
        "NAME,SIZE,TYPE,ROTA,MODEL,FSTYPE,MOUNTPOINT"
    ])

    if "output" not in result:
        return {"status": result["error"]}

    try:
        return json.loads(result["output"]).get("blockdevices", [])

    except (json.JSONDecodeError, TypeError):
        return {"status": "Unable to parse storage information"}


def get_gpu_info():
    result = run_command(["lspci"])

    if "output" not in result:
        return {"status": result["error"]}

    devices = [
        line.strip()
        for line in result["output"].splitlines()
        if any(
            term in line.lower()
            for term in [
                "vga compatible controller",
                "3d controller",
                "display controller"
            ]
        )
    ]

    return devices or ["No GPU information detected"]


def get_hardware_report():
    return {
        "operating_system": platform.platform(),
        "virtualization_note": (
            "Hardware information may represent virtualized "
            "resources rather than physical hardware."
        ),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "memory_slots": get_memory_slot_info(),
        "storage": get_storage_info(),
        "gpu": get_gpu_info()
    }


if __name__ == "__main__":
    print(json.dumps(get_hardware_report(), indent=4))
