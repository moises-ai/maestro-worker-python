import sys
from types import SimpleNamespace

from maestro_worker_python import health


def test_collect_health_metadata_reports_gpu_and_mig(monkeypatch):
    def run_nvidia_smi(*args):
        if not args:
            return "| NVIDIA-SMI 570.148.08  Driver Version: 570.148.08  CUDA Version: 13.3 |\n"
        if args == ("--query-gpu=name,driver_version,compute_cap", "--format=csv,noheader,nounits"):
            return "NVIDIA L4, 570.148.08, 8.9\n"
        if args == ("-L",):
            return (
                "GPU 0: NVIDIA A100 (UUID: GPU-1)\n"
                "  MIG 1g.10gb Device 0: (UUID: MIG-1)\n"
                "  MIG 1g.10gb Device 1: (UUID: MIG-2)\n"
            )
        raise AssertionError(args)

    monkeypatch.setattr(health, "_run_nvidia_smi", run_nvidia_smi)
    monkeypatch.setattr(health.metadata, "version", lambda _name: "4.2.0")
    monkeypatch.setenv("CUDA_VERSION", "13.0.2")
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(version=SimpleNamespace(cuda="12.4")))

    assert health.collect_health_metadata() == {
        "worker_version": "4.2.0",
        "hardware": {
            "cuda": {
                "driver_supported_version": "13.3",
                "container_version": "13.0.2",
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
    monkeypatch.setattr(health, "_run_nvidia_smi", lambda *_args: None)
    monkeypatch.setattr(health.metadata, "version", lambda _name: "4.2.0")
    monkeypatch.delenv("CUDA_VERSION", raising=False)
    monkeypatch.delenv("CUDA_MPS_ACTIVE_THREAD_PERCENTAGE", raising=False)
    monkeypatch.delitem(sys.modules, "torch", raising=False)

    assert health.collect_health_metadata() == {
        "worker_version": "4.2.0",
        "hardware": {
            "cuda": {
                "driver_supported_version": None,
                "container_version": None,
                "torch_build_version": None,
            },
            "gpus": [],
            "partitioning": None,
        },
    }


def test_collect_health_metadata_reports_detectable_mps_limit(monkeypatch):
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
    monkeypatch.setattr(health, "_run_nvidia_smi", run_nvidia_smi)
    monkeypatch.setattr(health.metadata, "version", lambda _name: "4.2.0")
    monkeypatch.delitem(sys.modules, "torch", raising=False)

    first = health.get_health_metadata()
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(version=SimpleNamespace(cuda="12.6")))
    second = health.get_health_metadata()

    assert first["hardware"]["cuda"]["torch_build_version"] is None
    assert second["hardware"]["cuda"]["torch_build_version"] == "12.6"
    assert calls == [
        (),
        ("--query-gpu=name,driver_version,compute_cap", "--format=csv,noheader,nounits"),
        ("-L",),
    ]
    health._get_host_metadata.cache_clear()
