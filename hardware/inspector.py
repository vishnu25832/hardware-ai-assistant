
import json
import os
import platform
import re
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
        return {
            "error": "Required utility is not installed",
            "details": command[0]
        }

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
                or f"Exit code: {result.returncode}"
            }

        return {"output": result.stdout}

    except subprocess.TimeoutExpired:
        return {"error": "Command execution timed out"}

    except OSError:
        return {
            "error": "Unable to execute command",
            "details": "The operating system could not start the utility."
        }


def get_os_info():
    """Return operating system and virtualization information."""

    try:
        release = platform.freedesktop_os_release()
        distribution = release.get(
            "PRETTY_NAME",
            "Unknown Linux distribution"
        )
    except (AttributeError, OSError):
        distribution = "Unknown Linux distribution"

    release_string = platform.release().lower()

    is_wsl = (
        "microsoft" in release_string
        or bool(os.environ.get("WSL_DISTRO_NAME"))
    )

    return {
        "system": platform.system(),
        "distribution": distribution,
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "environment": (
            "WSL2/WSL" if is_wsl else "Linux or other environment"
        ),
        "is_wsl": is_wsl
    }


def get_cpu_info():
    """Return normalized CPU information and its inspection scope."""

    os_info = get_os_info()

    info = {
        "architecture": platform.machine(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_processors": psutil.cpu_count(logical=True),
        "model": "Unavailable",
        "scope": (
            "CPU topology visible to the WSL environment. "
            "These counts do not necessarily represent the host "
            "laptop's complete physical CPU topology."
            if os_info["is_wsl"]
            else "CPU topology reported by the operating system."
        )
    }

    result = run_command(["lscpu"])

    if "output" not in result:
        info["status"] = result.get(
            "error",
            "CPU inspection unavailable"
        )
        info["details"] = result.get("details")
        return info

    for line in result["output"].splitlines():
        if line.startswith(("Model name:", "Model:")):
            info["model"] = line.split(":", 1)[1].strip()
            break

    return info


def get_memory_info():
    """Return memory usage visible to the current environment."""

    os_info = get_os_info()

    try:
        memory = psutil.virtual_memory()

        return {
            "total_gb": round(memory.total / (1024 ** 3), 2),
            "available_gb": round(memory.available / (1024 ** 3), 2),
            "used_gb": round(memory.used / (1024 ** 3), 2),
            "used_percent": memory.percent,
            "scope": (
                "Memory visible to the WSL environment. "
                "This may represent a WSL memory limit and must not "
                "be treated as the laptop's physical installed RAM."
                if os_info["is_wsl"]
                else "Memory visible to the current operating system."
            )
        }

    except Exception:
        return {
            "status": "Memory information unavailable",
            "scope": (
                "Memory visible to the current operating system."
            )
        }


def get_memory_slot_info():
    """Return sanitized BIOS memory-slot information when available."""

    result = run_command(["dmidecode", "-t", "memory"])

    if "output" not in result:
        return {
            "status": "Unavailable",
            "reason": result.get(
                "details",
                result.get("error", "Memory-slot inspection failed")
            ),
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

    if not re.search(
        r"^\s*Memory Device\s*$",
        output,
        re.IGNORECASE | re.MULTILINE
    ):
        return {
            "status": "Unavailable",
            "reason": "No memory-device information was returned"
        }

    maximum_capacity_gb = None
    total_slots = None
    modules = []

    blocks = re.split(r"\n\s*\n", output)

    for block in blocks:
        if "Physical Memory Array" in block:
            capacity_match = re.search(
                r"Maximum Capacity:\s*(\d+)\s*(GB|TB|MB)",
                block,
                re.IGNORECASE
            )

            if capacity_match:
                value = float(capacity_match.group(1))
                unit = capacity_match.group(2).upper()

                if unit == "TB":
                    maximum_capacity_gb = value * 1024
                elif unit == "MB":
                    maximum_capacity_gb = value / 1024
                else:
                    maximum_capacity_gb = value

            slots_match = re.search(
                r"Number Of Devices:\s*(\d+)",
                block,
                re.IGNORECASE
            )

            if slots_match:
                total_slots = int(slots_match.group(1))

        if not re.search(
            r"^\s*Memory Device\s*$",
            block,
            re.IGNORECASE | re.MULTILINE
        ):
            continue

        def extract(pattern):
            match = re.search(
                pattern,
                block,
                re.IGNORECASE | re.MULTILINE
            )
            return match.group(1).strip() if match else None

        size = extract(r"^\s*Size:\s*(.+)$")
        locator = extract(r"^\s*Locator:\s*(.+)$")
        memory_type = extract(r"^\s*Type:\s*(.+)$")
        speed = extract(r"^\s*Speed:\s*(.+)$")
        configured_speed = extract(
            r"^\s*Configured Memory Speed:\s*(.+)$"
        )

        installed = bool(
            size
            and size.lower() not in (
                "no module installed",
                "unknown",
                "not installed"
            )
        )

        modules.append({
            "locator": locator,
            "installed": installed,
            "size": size,
            "type": memory_type,
            "speed": speed,
            "configured_speed": configured_speed
        })

    installed_count = sum(
        1 for module in modules if module["installed"]
    )

    if total_slots is None:
        total_slots = len(modules) if modules else None

    free_slots = (
        max(total_slots - installed_count, 0)
        if total_slots is not None
        else None
    )

    return {
        "status": "Retrieved",
        "total_slots": total_slots,
        "installed_slots": installed_count,
        "free_slots": free_slots,
        "maximum_capacity_gb": maximum_capacity_gb,
        "modules": modules,
        "limitations": (
            "Maximum supported capacity and slot information "
            "may be unavailable or incomplete on virtualized systems."
        )
    }


def get_storage_info():
    """Return normalized storage information without mount-point paths."""

    result = run_command([
        "lsblk",
        "-J",
        "-o",
        "NAME,SIZE,TYPE,ROTA,MODEL,FSTYPE,MOUNTPOINT"
    ])

    if "output" not in result:
        return {
            "status": "Unavailable",
            "reason": result.get(
                "details",
                result.get("error", "Storage inspection failed")
            )
        }

    try:
        devices = json.loads(result["output"]).get(
            "blockdevices",
            []
        )

    except (json.JSONDecodeError, TypeError):
        return {
            "status": "Unable to parse storage information"
        }

    def normalize_device(device):
        name = device.get("name") or ""
        model = device.get("model") or ""
        device_type = device.get("type", "unknown")
        rota = device.get("rota")

        is_virtual = "virtual" in model.lower()

        if device_type != "disk":
            storage_kind = "partition or other device"
            interface = "Not applicable"

        elif is_virtual:
            storage_kind = "Virtual disk"
            interface = "Unknown"

        elif name.startswith("nvme"):
            storage_kind = "SSD"
            interface = "NVMe"

        elif rota is not None and str(rota).lower() in (
            "1", "true"
        ):
            storage_kind = "HDD"
            interface = "Unknown"

        elif rota is not None and str(rota).lower() in (
            "0", "false"
        ):
            storage_kind = "SSD"
            interface = "Unknown"

        else:
            storage_kind = "Unknown"
            interface = "Unknown"

        normalized = {
            "name": name,
            "size": device.get("size"),
            "device_type": device_type,
            "model": model or "Unknown",
            "storage_kind": storage_kind,
            "interface": interface,
            "filesystem": device.get("fstype")
        }

        children = device.get("children", [])

        if children:
            normalized["partitions"] = [
                normalize_device(child)
                for child in children
            ]

        return normalized

    if not devices:
        return {"status": "No storage devices detected"}

    return [
        normalize_device(device)
        for device in devices
    ]


def get_gpu_info():
    """Return detected graphics-controller information."""

    result = run_command(["lspci"])

    if "output" not in result:
        return {
            "status": "Unavailable",
            "reason": result.get(
                "details",
                result.get("error", "GPU inspection failed")
            )
        }

    devices = [
        line.strip()
        for line in result["output"].splitlines()
        if any(
            term in line.lower()
            for term in (
                "vga compatible controller",
                "3d controller",
                "display controller"
            )
        )
    ]

    return devices or ["No GPU information detected"]


def get_hardware_report():
    """Collect all available hardware information for diagnostics."""

    os_info = get_os_info()

    return {
        "operating_system": platform.platform(),
        "os_details": os_info,
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
