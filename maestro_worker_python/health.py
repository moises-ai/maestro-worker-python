import os
import re
import subprocess
import sys
from functools import lru_cache
from importlib import metadata
from typing import Any

import pynvml


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


def _partitioning_metadata(
    visible_mig_partitions: list[dict[str, int | None]],
) -> dict[str, Any] | None:
    if visible_mig_partitions:
        return {
            "method": "mig",
            "visible_partition_count": len(visible_mig_partitions),
            "visible_partitions": visible_mig_partitions,
        }

    configured_active_thread_percentage = None
    active_thread_percentage = os.getenv("CUDA_MPS_ACTIVE_THREAD_PERCENTAGE")
    if active_thread_percentage:
        try:
            percentage = int(active_thread_percentage)
        except ValueError:
            percentage = None
        if percentage is not None and 0 < percentage <= 100:
            configured_active_thread_percentage = percentage

    configured_pinned_device_memory_limit = (
        os.getenv("CUDA_MPS_PINNED_DEVICE_MEM_LIMIT") or None
    )
    if (
        configured_active_thread_percentage is None
        and configured_pinned_device_memory_limit is None
    ):
        return None

    return {
        "method": "mps",
        "configured_active_thread_percentage": configured_active_thread_percentage,
        "configured_pinned_device_memory_limit": configured_pinned_device_memory_limit,
        # MPS permits non-uniform client limits, so configured limits cannot
        # reliably reveal the total number of clients.
        "partition_count": None,
    }


def _nvidia_smi_driver_supported_cuda_version() -> str | None:
    """Fallback for environments where NVML cannot query the CUDA driver."""
    output = _run_nvidia_smi("-q") or ""
    match = re.search(r"CUDA(?: UMD)? Version\s*:\s*([0-9]+(?:\.[0-9]+)*)", output)
    return match.group(1) if match else None


def _nvml_mig_partition_metadata(device: Any) -> dict[str, int | None]:
    try:
        attributes = pynvml.nvmlDeviceGetAttributes(device)
    except pynvml.NVMLError:
        return {
            "gpu_instance_slice_count": None,
            "compute_instance_slice_count": None,
            "memory_size_mb": None,
        }

    return {
        "gpu_instance_slice_count": attributes.gpuInstanceSliceCount,
        "compute_instance_slice_count": attributes.computeInstanceSliceCount,
        "memory_size_mb": attributes.memorySizeMB,
    }


def _nvml_visible_mig_devices(device: Any) -> list[Any]:
    try:
        if pynvml.nvmlDeviceIsMigDeviceHandle(device):
            return [device]
    except pynvml.NVMLError:
        pass

    try:
        max_mig_devices = pynvml.nvmlDeviceGetMaxMigDeviceCount(device)
    except pynvml.NVMLError:
        return []

    mig_devices = []
    for mig_index in range(max_mig_devices):
        try:
            mig_device = pynvml.nvmlDeviceGetMigDeviceHandleByIndex(device, mig_index)
        except pynvml.NVMLError:
            continue
        mig_devices.append(mig_device)

    return mig_devices


def _nvml_device_identity(device: Any) -> str:
    try:
        return pynvml.nvmlDeviceGetUUID(device)
    except pynvml.NVMLError:
        return repr(device)


def _nvml_gpu_metadata() -> tuple[
    list[dict[str, str | None]], list[dict[str, int | None]]
]:
    """Collect visible GPUs and active MIG partitions."""
    try:
        device_count = pynvml.nvmlDeviceGetCount()
    except pynvml.NVMLError:
        return [], []

    gpus = []
    visible_mig_partitions = []
    seen_mig_devices = set()
    for device_index in range(device_count):
        try:
            device = pynvml.nvmlDeviceGetHandleByIndex(device_index)
        except pynvml.NVMLError:
            continue

        try:
            model = pynvml.nvmlDeviceGetName(device)
        except pynvml.NVMLError:
            model = None

        try:
            major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(device)
            sm_version = f"sm_{major}{minor}"
        except pynvml.NVMLError:
            sm_version = None

        gpus.append({"model": model, "sm_version": sm_version})

        for mig_device in _nvml_visible_mig_devices(device):
            identity = _nvml_device_identity(mig_device)
            if identity in seen_mig_devices:
                continue
            seen_mig_devices.add(identity)
            visible_mig_partitions.append(
                _nvml_mig_partition_metadata(mig_device)
            )

    return gpus, visible_mig_partitions


def _collect_hardware_metadata() -> dict[str, Any]:
    """Collect best-effort hardware metadata through one NVML session."""
    driver_version = None
    driver_supported_cuda_version = None
    gpus = []
    visible_mig_partitions = []

    try:
        pynvml.nvmlInit()
    except pynvml.NVMLError:
        pass
    else:
        try:
            try:
                driver_version = pynvml.nvmlSystemGetDriverVersion()
            except pynvml.NVMLError:
                pass

            try:
                cuda_version = pynvml.nvmlSystemGetCudaDriverVersion_v2()
                major = cuda_version // 1000
                minor = (cuda_version % 1000) // 10
                driver_supported_cuda_version = f"{major}.{minor}"
            except pynvml.NVMLError:
                pass

            gpus, visible_mig_partitions = _nvml_gpu_metadata()
        finally:
            try:
                pynvml.nvmlShutdown()
            except pynvml.NVMLError:
                pass

    if driver_supported_cuda_version is None:
        driver_supported_cuda_version = _nvidia_smi_driver_supported_cuda_version()

    return {
        "nvidia_driver_version": driver_version,
        "cuda": {
            "driver_supported_version": driver_supported_cuda_version,
        },
        "gpus": gpus,
        "partitioning": _partitioning_metadata(visible_mig_partitions),
    }


def _torch_cuda_version() -> str | None:
    """CUDA toolkit version used to build an already-imported torch module."""
    torch = sys.modules.get("torch")
    return getattr(getattr(torch, "version", None), "cuda", None)


def _torch_observed_sm_count() -> int | None:
    """SMs visible to an already-initialized Torch CUDA runtime."""
    torch = sys.modules.get("torch")
    cuda = getattr(torch, "cuda", None)
    is_initialized = getattr(cuda, "is_initialized", None)
    if not callable(is_initialized):
        return None

    try:
        if not is_initialized():
            return None
        device = cuda.current_device()
        sm_count = cuda.get_device_properties(device).multi_processor_count
    except Exception:
        return None

    return sm_count if isinstance(sm_count, int) and sm_count > 0 else None


def _worker_version() -> str:
    try:
        return metadata.version("maestro-worker-python")
    except metadata.PackageNotFoundError:
        return "unknown"


def _collect_host_metadata() -> dict[str, Any]:
    """Collect stable host metadata without making health depend on a GPU."""
    return {
        "worker_version": _worker_version(),
        "hardware": _collect_hardware_metadata(),
    }


@lru_cache(maxsize=1)
def _get_host_metadata() -> dict[str, Any]:
    return _collect_host_metadata()


def _with_process_metadata(host_metadata: dict[str, Any]) -> dict[str, Any]:
    hardware = host_metadata["hardware"]
    partitioning = hardware["partitioning"]
    if partitioning and partitioning["method"] == "mps":
        partitioning = {
            **partitioning,
            "observed_sm_count": _torch_observed_sm_count(),
        }

    return {
        **host_metadata,
        "hardware": {
            **hardware,
            "partitioning": partitioning,
            "cuda": {
                **hardware["cuda"],
                "torch_build_version": _torch_cuda_version(),
            },
        },
    }


def collect_health_metadata() -> dict[str, Any]:
    """Collect fresh host and process metadata."""
    return _with_process_metadata(_collect_host_metadata())


def get_health_metadata() -> dict[str, Any]:
    """Return cached host metadata plus current process-local metadata."""
    return _with_process_metadata(_get_host_metadata())
