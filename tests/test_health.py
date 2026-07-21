import sys
from types import SimpleNamespace

import pytest

from maestro_worker_python import health


def test_nvml_driver_supported_cuda_version(monkeypatch):
    calls = []

    monkeypatch.setattr(health.pynvml, "nvmlInit", lambda: calls.append("init"))
    monkeypatch.setattr(
        health.pynvml,
        "nvmlSystemGetCudaDriverVersion_v2",
        lambda: calls.append("query") or 13030,
    )
    monkeypatch.setattr(health.pynvml, "nvmlShutdown", lambda: calls.append("shutdown"))

    assert health._nvml_driver_supported_cuda_version() == "13.3"
    assert calls == ["init", "query", "shutdown"]


def test_nvml_driver_supported_cuda_version_shuts_down_after_query_error(monkeypatch):
    calls = []

    def query():
        calls.append("query")
        raise health.pynvml.NVMLError(health.pynvml.NVML_ERROR_UNKNOWN)

    monkeypatch.setattr(health.pynvml, "nvmlInit", lambda: calls.append("init"))
    monkeypatch.setattr(health.pynvml, "nvmlSystemGetCudaDriverVersion_v2", query)
    monkeypatch.setattr(health.pynvml, "nvmlShutdown", lambda: calls.append("shutdown"))

    assert health._nvml_driver_supported_cuda_version() is None
    assert calls == ["init", "query", "shutdown"]


def test_nvml_driver_supported_cuda_version_degrades_when_initialization_fails(
    monkeypatch,
):
    def init():
        raise health.pynvml.NVMLError(health.pynvml.NVML_ERROR_LIBRARY_NOT_FOUND)

    monkeypatch.setattr(health.pynvml, "nvmlInit", init)
    monkeypatch.setattr(
        health.pynvml,
        "nvmlShutdown",
        lambda: pytest.fail("NVML must not be shut down after failed initialization"),
    )

    assert health._nvml_driver_supported_cuda_version() is None


@pytest.mark.parametrize("label", ["CUDA Version", "CUDA UMD Version"])
def test_driver_supported_cuda_version_falls_back_to_nvidia_smi(monkeypatch, label):
    monkeypatch.setattr(health, "_nvml_driver_supported_cuda_version", lambda: None)
    monkeypatch.setattr(
        health,
        "_run_nvidia_smi",
        lambda *args: f"{label} : 13.3\n" if args == ("-q",) else None,
    )

    assert health._driver_supported_cuda_version() == "13.3"


def test_collect_health_metadata_reports_gpu_and_mig(monkeypatch):
    def run_nvidia_smi(*args):
        if args == (
            "--query-gpu=name,driver_version,compute_cap",
            "--format=csv,noheader,nounits",
        ):
            return "NVIDIA L4, 570.148.08, 8.9\n"
        if args == ("-L",):
            return (
                "GPU 0: NVIDIA A100 (UUID: GPU-1)\n"
                "  MIG 1g.10gb Device 0: (UUID: MIG-1)\n"
                "  MIG 1g.10gb Device 1: (UUID: MIG-2)\n"
            )
        raise AssertionError(args)

    monkeypatch.setattr(health, "_nvml_driver_supported_cuda_version", lambda: "13.3")
    monkeypatch.setattr(health, "_run_nvidia_smi", run_nvidia_smi)
    monkeypatch.setattr(health.metadata, "version", lambda _name: "4.2.0")
    monkeypatch.setitem(
        sys.modules, "torch", SimpleNamespace(version=SimpleNamespace(cuda="12.4"))
    )

    assert health.collect_health_metadata() == {
        "worker_version": "4.2.0",
        "hardware": {
            "cuda": {
                "driver_supported_version": "13.3",
                "torch_build_version": "12.4",
            },
            "gpus": [
                {
                    "model": "NVIDIA L4",
                    "driver_version": "570.148.08",
                    "sm_version": "sm_89",
                }
            ],
            "partitioning": {
                "method": "mig",
                "visible_partition_count": 2,
            },
        },
    }


def test_collect_health_metadata_degrades_without_nvidia(monkeypatch):
    monkeypatch.setattr(health, "_nvml_driver_supported_cuda_version", lambda: None)
    monkeypatch.setattr(health, "_run_nvidia_smi", lambda *_args: None)
    monkeypatch.setattr(health.metadata, "version", lambda _name: "4.2.0")
    monkeypatch.delenv("CUDA_MPS_ACTIVE_THREAD_PERCENTAGE", raising=False)
    monkeypatch.delitem(sys.modules, "torch", raising=False)

    assert health.collect_health_metadata() == {
        "worker_version": "4.2.0",
        "hardware": {
            "cuda": {
                "driver_supported_version": None,
                "torch_build_version": None,
            },
            "gpus": [],
            "partitioning": None,
        },
    }


def test_collect_health_metadata_reports_detectable_mps_limit(monkeypatch):
    monkeypatch.setattr(health, "_nvml_driver_supported_cuda_version", lambda: None)
    monkeypatch.setattr(health, "_run_nvidia_smi", lambda *_args: "")
    monkeypatch.setattr(health.metadata, "version", lambda _name: "4.2.0")
    monkeypatch.setenv("CUDA_MPS_ACTIVE_THREAD_PERCENTAGE", "50")

    metadata = health.collect_health_metadata()

    assert metadata["hardware"]["partitioning"] == {
        "method": "mps",
        "active_thread_percentage": 50,
        "partition_count": None,
    }


def test_cached_health_refreshes_torch_version_without_reprobing_host(monkeypatch):
    calls = []

    def run_nvidia_smi(*args):
        calls.append(args)
        return ""

    health._get_host_metadata.cache_clear()
    monkeypatch.setattr(health, "_nvml_driver_supported_cuda_version", lambda: None)
    monkeypatch.setattr(health, "_run_nvidia_smi", run_nvidia_smi)
    monkeypatch.setattr(health.metadata, "version", lambda _name: "4.2.0")
    monkeypatch.delitem(sys.modules, "torch", raising=False)

    first = health.get_health_metadata()
    monkeypatch.setitem(
        sys.modules, "torch", SimpleNamespace(version=SimpleNamespace(cuda="12.6"))
    )
    second = health.get_health_metadata()

    assert first["hardware"]["cuda"]["torch_build_version"] is None
    assert second["hardware"]["cuda"]["torch_build_version"] == "12.6"
    assert calls == [
        ("-q",),
        (
            "--query-gpu=name,driver_version,compute_cap",
            "--format=csv,noheader,nounits",
        ),
        ("-L",),
    ]
    health._get_host_metadata.cache_clear()
