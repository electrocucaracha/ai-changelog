"""Tests for opt-in telemetry collection and export."""

# pylint: disable=protected-access

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from ai_changelog import telemetry


def test_run_metrics_ignores_invalid_values_and_returns_snapshot() -> None:
    """Ignore invalid measurements and return accumulated values."""
    metrics = telemetry.RunMetrics()

    metrics.add("valid", 2)
    metrics.add("negative", -1)
    metrics.add("infinite", math.inf)
    metrics.add("nan", math.nan)

    assert metrics.snapshot() == {"valid": 2}


def test_add_records_only_when_metrics_are_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Record measurements only while an invocation is active."""
    metrics = telemetry.RunMetrics()
    monkeypatch.setattr(telemetry, "_active", None)
    telemetry.add("ignored")
    monkeypatch.setattr(telemetry, "_active", metrics)
    telemetry.add("recorded", 3)

    assert metrics.snapshot() == {"recorded": 3}


def test_request_without_active_metrics_is_a_noop() -> None:
    """Skip request recording when telemetry is disabled."""
    with telemetry.request("model", "completion") as record:
        record(SimpleNamespace(usage=SimpleNamespace(prompt_tokens=1)))


def test_request_records_usage_and_pricing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Capture token counts, pricing, and request duration."""
    metrics = telemetry.RunMetrics()
    monkeypatch.setattr(telemetry, "_active", metrics)
    monkeypatch.setattr("litellm.completion_cost", lambda **_: 0.25)
    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=5, completion_tokens=7)
    )

    with telemetry.request("model", "completion") as record:
        record(response)

    values = metrics.snapshot()
    assert values["completion.requests"] == 1
    assert values["completion.input_tokens"] == 5
    assert values["completion.output_tokens"] == 7
    assert values["cost_estimated"] == 0.25
    assert values["cost_priced_requests"] == 1
    assert values["completion.duration"] >= 0


def test_request_counts_failures_and_survives_pricing_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Count failed requests without failing on unavailable pricing."""
    metrics = telemetry.RunMetrics()
    monkeypatch.setattr(telemetry, "_active", metrics)

    def fail_pricing(**_: object) -> float:
        raise RuntimeError("pricing unavailable")

    monkeypatch.setattr("litellm.completion_cost", fail_pricing)
    with (
        pytest.raises(RuntimeError, match="request failed"),
        telemetry.request("model", "completion") as record,
    ):
        record(SimpleNamespace(usage=SimpleNamespace(prompt_tokens=2)))
        raise RuntimeError("request failed")

    values = metrics.snapshot()
    assert values["completion.failures"] == 1
    assert values["completion.input_tokens"] == 2
    assert values["completion.duration"] >= 0
    assert "cost_estimated" not in values


@pytest.mark.parametrize(
    "endpoint",
    [
        "ftp://collector.test/metrics",
        "http:///metrics",
        "http://user@collector.test/metrics",
        "http://collector.test/metrics?debug=true",
        "http://collector.test/metrics#fragment",
    ],
)
def test_instrument_cli_ignores_invalid_endpoints(
    monkeypatch: pytest.MonkeyPatch, endpoint: str
) -> None:
    """Run normally and avoid exporting for invalid endpoints."""
    exported: list[telemetry.RunMetrics] = []
    monkeypatch.setenv(telemetry.ENDPOINT_ENV, endpoint)
    monkeypatch.setattr(
        telemetry, "_export", lambda _endpoint, metrics: exported.append(metrics)
    )

    @telemetry.instrument_cli
    def run() -> str:
        return "result"

    assert run() == "result"
    assert not exported


def test_instrument_cli_exports_success_and_restores_active_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Export successful invocations and restore the previous context."""
    previous = telemetry.RunMetrics()
    exported: list[tuple[str, telemetry.RunMetrics]] = []
    monkeypatch.setattr(telemetry, "_active", previous)
    monkeypatch.setenv(telemetry.ENDPOINT_ENV, " https://collector.test/metrics ")
    monkeypatch.setattr(
        telemetry,
        "_export",
        lambda endpoint, metrics: exported.append((endpoint, metrics)),
    )

    @telemetry.instrument_cli
    def run() -> str:
        telemetry.add("commits", 4)
        return "result"

    assert run() == "result"
    assert telemetry._active is previous
    assert len(exported) == 1
    endpoint, metrics = exported[0]
    assert endpoint == "https://collector.test/metrics"
    assert metrics.outcome == "success"
    assert metrics.snapshot() == {"commits": 4}


@pytest.mark.parametrize(
    ("exception", "outcome"),
    [(RuntimeError("failed"), "error"), (SystemExit(0), "success")],
)
def test_instrument_cli_exports_failures_and_reraises(
    monkeypatch: pytest.MonkeyPatch,
    exception: BaseException,
    outcome: str,
) -> None:
    """Export invocation outcome and propagate the original exception."""
    exported: list[telemetry.RunMetrics] = []
    monkeypatch.setenv(telemetry.ENDPOINT_ENV, "http://collector.test/metrics")
    monkeypatch.setattr(
        telemetry,
        "_export",
        lambda _endpoint, metrics: exported.append(metrics),
    )

    @telemetry.instrument_cli
    def run() -> None:
        raise exception

    with pytest.raises(type(exception)):
        run()

    assert exported[0].outcome == outcome


def test_export_sends_counters_and_histograms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Send accumulated measurements and shut down the exporter."""
    exports: list[tuple[object, int]] = []
    shutdowns: list[bool] = []

    class FakeExporter:
        """Capture export calls without making a network request."""

        def __init__(self, *, endpoint: str, timeout: int) -> None:
            """Check exporter configuration."""
            assert endpoint == "http://collector.test/metrics"
            assert timeout == 1

        def export(self, data: object, *, timeout_millis: int) -> None:
            """Capture the metric payload and timeout."""
            exports.append((data, timeout_millis))

        def shutdown(self) -> None:
            """Record exporter shutdown."""
            shutdowns.append(True)

    monkeypatch.setattr(
        "opentelemetry.exporter.otlp.proto.http.metric_exporter.OTLPMetricExporter",
        FakeExporter,
    )
    metrics = telemetry.RunMetrics()
    metrics.outcome = "success"
    metrics.add("commits", 2)
    metrics.add("cost_estimated", 0.5)
    metrics.add("completion.duration", 0.1)

    telemetry._export("http://collector.test/metrics", metrics)

    assert len(exports) == 1
    assert exports[0][0] is not None
    assert exports[0][1] == 1000
    assert shutdowns == [True]
