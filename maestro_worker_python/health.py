import csv
import os
import subprocess
import sys
from functools import lru_cache
from importlib import metadata
from io import StringIO
from typing import Any


def _run_nvidia_smi(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", *args],
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    return result.stdout


def _gpu_metadata() -> list[dict[str, str | None]]:
    output = _run_nvidia_smi(
        "--query-gpu=name,driver_version,compute_cap",
        "--format=csv,noheader,nounits",
    )
    if not output:
        return []

    gpus = []
    for row in csv.reader(StringIO(output), skipinitialspace=True):
        if len(row) != 3:
            continue
        model, driver_version, compute_capability = (value.strip() for value in row)
        sm_version = None
        if compute_capability and compute_capability.lower() not in {"n/a", "[n/a]"}:
            sm_version = f"sm_{compute_capability.replace('.', '')}"
        gpus.append(
            {
                "model": model or None,
                "driver_version": driver_version or None,
                "sm_version": sm_version,
            }
        )
    return gpus


def _partitioning_metadata() -> dict[str, Any] | None:
    device_list = _run_nvidia_smi("-L") or ""
    visible_mig_devices = sum(
        line.strip().startswith("MIG ") for line in device_list.splitlines()
    )
    if visible_mig_devices:
        return {
            "method": "mig",
            "visible_partition_count": visible_mig_devices,
        }

    active_thread_percentage = os.getenv("CUDA_MPS_ACTIVE_THREAD_PERCENTAGE")
    if active_thread_percentage:
        try:
            percentage = int(active_thread_percentage)
        except ValueError:
            return None
        if 0 < percentage <= 100:
            return {
                "method": "mps",
                "active_thread_percentage": percentage,
                # MPS permits non-uniform client limits, so this percentage
                # cannot reliably reveal the total number of clients.
                "partition_count": None,
            }
    return None


def _cuda_version() -> str | None:
    torch = sys.modules.get("torch")
    torch_version = getattr(getattr(torch, "version", None), "cuda", None)
    return torch_version or os.getenv("CUDA_VERSION")


def _worker_version() -> str:
    try:
        return metadata.version("maestro-worker-python")
    except metadata.PackageNotFoundError:
        return "unknown"


def collect_health_metadata() -> dict[str, Any]:
    """Collect stable runtime metadata without making health depend on a GPU."""
    return {
        "worker_version": _worker_version(),
        "hardware": {
            "cuda_version": _cuda_version(),
            "gpus": _gpu_metadata(),
            "partitioning": _partitioning_metadata(),
        },
    }


@lru_cache(maxsize=1)
def get_health_metadata() -> dict[str, Any]:
    """Return process-lifetime metadata; hardware does not change at runtime."""
    return collect_health_metadata()
