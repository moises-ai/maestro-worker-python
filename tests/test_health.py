import sys
from types import SimpleNamespace

import pytest

from maestro_worker_python import health


@pytest.fixture
def nvml_host(monkeypatch):
    lifecycle = []
    monkeypatch.setattr(health.pynvml, "nvmlInit", lambda: lifecycle.append("init"))
    monkeypatch.setattr(
        health.pynvml, "nvmlShutdown", lambda: lifecycle.append("shutdown")
    )
    monkeypatch.setattr(health.pynvml, "nvmlSystemGetDriverVersion", lambda: "610.12")
    monkeypatch.setattr(
        health.pynvml, "nvmlSystemGetCudaDriverVersion_v2", lambda: 13030
    )
    monkeypatch.setattr(health.pynvml, "nvmlDeviceGetCount", lambda: 0)
    monkeypatch.setattr(
        health,
        "_run_nvidia_smi",
        lambda *_args: pytest.fail("nvidia-smi fallback should not run"),
    )
    monkeypatch.delenv("CUDA_MPS_ACTIVE_THREAD_PERCENTAGE", raising=False)
    monkeypatch.delenv("CUDA_MPS_PINNED_DEVICE_MEM_LIMIT", raising=False)
    monkeypatch.delitem(sys.modules, "torch", raising=False)
    return lifecycle


def test_collect_health_metadata_reports_nvml_gpu_and_visible_mig(
    monkeypatch, nvml_host
):
    def mig_device(_device, index):
        if index in {0, 2}:
            return f"mig-{index}"
        raise health.pynvml.NVMLError(health.pynvml.NVML_ERROR_NOT_FOUND)

    monkeypatch.setattr(health.pynvml, "nvmlDeviceGetCount", lambda: 1)
    monkeypatch.setattr(
        health.pynvml, "nvmlDeviceGetHandleByIndex", lambda _index: "gpu-0"
    )
    monkeypatch.setattr(
        health.pynvml, "nvmlDeviceGetName", lambda _device: "NVIDIA H100"
    )
    monkeypatch.setattr(
        health.pynvml,
        "nvmlDeviceGetCudaComputeCapability",
        lambda _device: (9, 0),
    )
    monkeypatch.setattr(
        health.pynvml, "nvmlDeviceGetMaxMigDeviceCount", lambda _device: 3
    )
    monkeypatch.setattr(
        health.pynvml, "nvmlDeviceGetMigDeviceHandleByIndex", mig_device
    )
    monkeypatch.setattr(health.metadata, "version", lambda _name: "4.2.0")
    monkeypatch.setitem(
        sys.modules, "torch", SimpleNamespace(version=SimpleNamespace(cuda="12.4"))
    )

    assert health.collect_health_metadata() == {
        "worker_version": "4.2.0",
        "hardware": {
            "nvidia_driver_version": "610.12",
            "cuda": {
                "driver_supported_version": "13.3",
                "torch_build_version": "12.4",
            },
            "gpus": [{"model": "NVIDIA H100", "sm_version": "sm_90"}],
            "partitioning": {
                "method": "mig",
                "visible_partition_count": 2,
            },
        },
    }
    assert nvml_host == ["init", "shutdown"]


@pytest.mark.parametrize("label", ["CUDA Version", "CUDA UMD Version"])
def test_collect_health_metadata_falls_back_for_cuda_driver_version(
    monkeypatch, nvml_host, label
):
    def cuda_driver_version():
        raise health.pynvml.NVMLError(health.pynvml.NVML_ERROR_FUNCTION_NOT_FOUND)

    monkeypatch.setattr(
        health.pynvml, "nvmlSystemGetCudaDriverVersion_v2", cuda_driver_version
    )
    monkeypatch.setattr(
        health,
        "_run_nvidia_smi",
        lambda *args: f"{label} : 13.3\n" if args == ("-q",) else None,
    )

    metadata = health.collect_health_metadata()

    assert metadata["hardware"]["nvidia_driver_version"] == "610.12"
    assert metadata["hardware"]["cuda"] == {
        "driver_supported_version": "13.3",
        "torch_build_version": None,
    }
    assert nvml_host == ["init", "shutdown"]


def test_collect_health_metadata_keeps_partial_nvml_results(monkeypatch, nvml_host):
    def driver_version():
        raise health.pynvml.NVMLError(health.pynvml.NVML_ERROR_UNKNOWN)

    def model(_device):
        raise health.pynvml.NVMLError(health.pynvml.NVML_ERROR_UNKNOWN)

    def mig_count(_device):
        raise health.pynvml.NVMLError(health.pynvml.NVML_ERROR_NOT_SUPPORTED)

    monkeypatch.setattr(health.pynvml, "nvmlSystemGetDriverVersion", driver_version)
    monkeypatch.setattr(health.pynvml, "nvmlDeviceGetCount", lambda: 1)
    monkeypatch.setattr(
        health.pynvml, "nvmlDeviceGetHandleByIndex", lambda _index: "gpu-0"
    )
    monkeypatch.setattr(health.pynvml, "nvmlDeviceGetName", model)
    monkeypatch.setattr(
        health.pynvml,
        "nvmlDeviceGetCudaComputeCapability",
        lambda _device: (8, 9),
    )
    monkeypatch.setattr(health.pynvml, "nvmlDeviceGetMaxMigDeviceCount", mig_count)

    metadata = health.collect_health_metadata()

    assert metadata["hardware"]["nvidia_driver_version"] is None
    assert metadata["hardware"]["cuda"]["driver_supported_version"] == "13.3"
    assert metadata["hardware"]["gpus"] == [{"model": None, "sm_version": "sm_89"}]
    assert metadata["hardware"]["partitioning"] is None
    assert nvml_host == ["init", "shutdown"]


def test_collect_health_metadata_degrades_without_nvidia(monkeypatch, nvml_host):
    def init():
        raise health.pynvml.NVMLError(health.pynvml.NVML_ERROR_LIBRARY_NOT_FOUND)

    monkeypatch.setattr(health.pynvml, "nvmlInit", init)
    monkeypatch.setattr(health, "_run_nvidia_smi", lambda *_args: None)
    monkeypatch.setattr(health.metadata, "version", lambda _name: "4.2.0")

    assert health.collect_health_metadata() == {
        "worker_version": "4.2.0",
        "hardware": {
            "nvidia_driver_version": None,
            "cuda": {
                "driver_supported_version": None,
                "torch_build_version": None,
            },
            "gpus": [],
            "partitioning": None,
        },
    }
    assert nvml_host == []


def test_collect_health_metadata_reports_configured_mps_limits(monkeypatch, nvml_host):
    monkeypatch.setenv("CUDA_MPS_ACTIVE_THREAD_PERCENTAGE", "50")
    monkeypatch.setenv("CUDA_MPS_PINNED_DEVICE_MEM_LIMIT", "0=11517M")

    metadata = health.collect_health_metadata()

    assert metadata["hardware"]["partitioning"] == {
        "method": "mps",
        "configured_active_thread_percentage": 50,
        "configured_pinned_device_memory_limit": "0=11517M",
        "partition_count": None,
    }
    assert nvml_host == ["init", "shutdown"]


def test_collect_health_metadata_detects_mps_from_memory_limit(monkeypatch, nvml_host):
    monkeypatch.setenv("CUDA_MPS_ACTIVE_THREAD_PERCENTAGE", "invalid")
    monkeypatch.setenv("CUDA_MPS_PINNED_DEVICE_MEM_LIMIT", "0=11517M")

    metadata = health.collect_health_metadata()

    assert metadata["hardware"]["partitioning"] == {
        "method": "mps",
        "configured_active_thread_percentage": None,
        "configured_pinned_device_memory_limit": "0=11517M",
        "partition_count": None,
    }
    assert nvml_host == ["init", "shutdown"]


def test_cached_health_refreshes_torch_version_without_reprobing_host(
    monkeypatch, nvml_host
):
    health._get_host_metadata.cache_clear()
    monkeypatch.setattr(health.metadata, "version", lambda _name: "4.2.0")

    first = health.get_health_metadata()
    monkeypatch.setitem(
        sys.modules, "torch", SimpleNamespace(version=SimpleNamespace(cuda="12.6"))
    )
    second = health.get_health_metadata()

    assert first["hardware"]["cuda"]["torch_build_version"] is None
    assert second["hardware"]["cuda"]["torch_build_version"] == "12.6"
    assert nvml_host == ["init", "shutdown"]
    health._get_host_metadata.cache_clear()
