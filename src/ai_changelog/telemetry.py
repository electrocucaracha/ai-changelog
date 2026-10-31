"""Opt-in, content-free OpenTelemetry metrics for AI Changelog runs."""

# pylint: disable=broad-exception-caught
# pylint: disable=import-outside-toplevel

from __future__ import annotations

import logging
import math
import os
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from typing import Any
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)
ENDPOINT_ENV = "CHANGELOG_TELEMETRY_ENDPOINT"
_active: RunMetrics | None = None  # pylint: disable=invalid-name


class RunMetrics:
    """Accumulate numeric measurements without retaining prompt content."""

    def __init__(self) -> None:
        self.started = time.monotonic()
        self.outcome = "error"
        self.values: defaultdict[str, int | float] = defaultdict(int)
        self.lock = threading.Lock()

    def add(self, name: str, value: float = 1) -> None:
        """Add a finite, non-negative measurement safely across workers."""
        if math.isfinite(value) and value >= 0:
            with self.lock:
                self.values[name] += value

    def snapshot(self) -> dict[str, float]:
        """Return a thread-safe copy of accumulated measurements."""
        with self.lock:
            return dict(self.values)


def add(name: str, value: float = 1) -> None:
    """Record a measurement for the active CLI invocation, if enabled."""
    if _active is not None:
        _active.add(name, value)


@contextmanager
def request(model: str, stage: str) -> Iterator[Callable[[Any], None]]:
    """Measure one logical AI request without exporting its content."""
    metrics = _active
    if metrics is None:
        yield lambda _response: None
        return

    started = time.monotonic()
    metrics.add(f"{stage}.requests")

    def record(response: Any) -> None:
        try:
            usage = getattr(response, "usage", None)
            if usage is None:
                return

            for source, target in (
                ("prompt_tokens", f"{stage}.input_tokens"),
                ("completion_tokens", f"{stage}.output_tokens"),
            ):
                value = getattr(usage, source, None)
                if isinstance(value, (int, float)):
                    metrics.add(target, value)

            try:
                import litellm

                cost = litellm.completion_cost(
                    completion_response=response,
                    model=model,
                )
                if cost is not None:
                    metrics.add("cost_estimated", cost)
                    metrics.add("cost_priced_requests")
            except Exception:  # noqa: BLE001
                logger.debug("AI request pricing is unavailable.")
        except Exception:  # noqa: BLE001
            logger.debug("AI request usage metrics are unavailable.")

    try:
        yield record
    except Exception:
        metrics.add(f"{stage}.failures")
        raise
    finally:
        metrics.add(f"{stage}.duration", time.monotonic() - started)


# pylint: disable=too-many-locals
def _export(endpoint: str, metrics: RunMetrics) -> None:
    """Export one invocation using delta temporality and a short timeout."""
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.sdk.metrics import Counter, Histogram, MeterProvider
    from opentelemetry.sdk.metrics.export import (
        AggregationTemporality,
        InMemoryMetricReader,
    )
    from opentelemetry.sdk.resources import Resource

    reader = InMemoryMetricReader(
        preferred_temporality={
            Counter: AggregationTemporality.DELTA,
            Histogram: AggregationTemporality.DELTA,
        }
    )
    provider = MeterProvider(
        metric_readers=[reader],
        resource=Resource({"service.name": "ai-changelog"}),
        shutdown_on_exit=False,
    )
    exporter = None
    try:
        meter = provider.get_meter("ai_changelog")
        attributes = {"outcome": metrics.outcome}
        meter.create_counter("ai_changelog.invocations").add(1, attributes)

        measurements = metrics.snapshot()
        measurements["duration"] = time.monotonic() - metrics.started
        for name, value in measurements.items():
            full_name = f"ai_changelog.{name}"
            if name.endswith("duration") or name == "duration":
                meter.create_histogram(full_name, unit="s").record(value, attributes)
            else:
                unit = "USD" if name == "cost_estimated" else "1"
                meter.create_counter(full_name, unit=unit).add(value, attributes)

        data = reader.get_metrics_data()
        if data is not None:
            exporter = OTLPMetricExporter(endpoint=endpoint, timeout=1)
            exporter.export(data, timeout_millis=1000)
    finally:
        if exporter is not None:
            exporter.shutdown()
        provider.shutdown()


def instrument_cli(function: Callable[..., Any]) -> Callable[..., Any]:
    """Collect metrics only when a valid endpoint is explicitly configured."""

    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        global _active  # pylint: disable=global-statement

        endpoint = os.getenv(ENDPOINT_ENV, "").strip()
        if not endpoint:
            return function(*args, **kwargs)

        try:
            parsed = urlsplit(endpoint)
            invalid_endpoint = any(
                (
                    parsed.scheme not in {"http", "https"},
                    not parsed.hostname,
                    parsed.username is not None,
                    parsed.password is not None,
                    bool(parsed.query),
                    bool(parsed.fragment),
                )
            )
            if invalid_endpoint:
                raise ValueError("Invalid telemetry endpoint")
        except ValueError:
            logger.warning("Telemetry disabled: endpoint must be an HTTP(S) URL.")
            return function(*args, **kwargs)

        metrics = RunMetrics()
        previous, _active = _active, metrics
        try:
            result = function(*args, **kwargs)
        except SystemExit as error:
            metrics.outcome = "error" if error.code else "success"
            raise
        except Exception:
            metrics.outcome = "error"
            raise
        else:
            metrics.outcome = "success"
            return result
        finally:
            _active = previous
            try:
                _export(endpoint, metrics)
            except Exception:  # noqa: BLE001
                logger.warning("Telemetry export unavailable; continuing without it.")

    return wrapped
