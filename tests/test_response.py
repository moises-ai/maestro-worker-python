from maestro_worker_python.response import WorkerResponse


def test_worker_response_preserves_fractional_billable_seconds():
    response = WorkerResponse(
        billable_seconds=42.711293,
        stats={"duration": 1.25},
        result={},
    )

    assert response.billable_seconds == 42.711293


def test_worker_response_accepts_integer_billable_seconds():
    response = WorkerResponse(
        billable_seconds=42,
        stats={"duration": 1.25},
        result={},
    )

    assert response.billable_seconds == 42.0
