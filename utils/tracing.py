#!/usr/bin/env python3
"""
Distributed Tracing - OpenTelemetry Integration
================================================
Provides distributed tracing for all agent operations.

Features:
- OpenTelemetry integration
- Trace all agent operations end-to-end
- Correlation IDs for request tracking
- Span context propagation
"""

import os
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

for d in [STATE, RUNTIME, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

TRACES_FILE = STATE / "traces.json"

# Try to import OpenTelemetry
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource

    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False
    print("[tracing] OpenTelemetry not available, using fallback", flush=True)


class SimpleTracer:
    """Simple tracing implementation (fallback when OpenTelemetry not available)."""

    def __init__(self):
        self.traces = []
        self.active_spans = {}

    def start_span(self, name: str, context: Optional[dict[str, Any]] = None) -> str:
        """Start a new span."""
        span_id = str(uuid.uuid4())
        trace_id = context.get("trace_id") if context else str(uuid.uuid4())
        parent_span_id = context.get("span_id") if context else None

        span = {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "name": name,
            "start_time": datetime.now(UTC).isoformat(),
            "attributes": {},
            "events": [],
        }

        self.active_spans[span_id] = span
        return span_id

    def end_span(self, span_id: str, status: str = "OK", error: Optional[str] = None) -> None:
        """End a span."""
        if span_id in self.active_spans:
            span = self.active_spans[span_id]
            span["end_time"] = datetime.now(UTC).isoformat()
            span["status"] = status
            if error:
                span["error"] = error
                span["events"].append({"name": "error", "message": error, "timestamp": datetime.now(UTC).isoformat()})

            self.traces.append(span)
            del self.active_spans[span_id]

            # Save traces periodically
            if len(self.traces) % 100 == 0:
                self._save_traces()

    def add_attribute(self, span_id: str, key: str, value: Any) -> None:
        """Add attribute to span."""
        if span_id in self.active_spans:
            self.active_spans[span_id]["attributes"][key] = str(value)

    def add_event(self, span_id: str, name: str, attributes: Optional[dict[str, Any]] = None) -> None:
        """Add event to span."""
        if span_id in self.active_spans:
            event = {
                "name": name,
                "timestamp": datetime.now(UTC).isoformat(),
                "attributes": attributes or {},
            }
            self.active_spans[span_id]["events"].append(event)

    def _save_traces(self) -> None:
        """Save traces to file."""
        try:
            # Keep only last 1000 traces
            if len(self.traces) > 1000:
                self.traces = self.traces[-1000:]

            TRACES_FILE.write_text(json.dumps(self.traces, indent=2))
        except Exception:
            pass


# Global tracer instance
_tracer: Optional[Any] = None
_simple_tracer = SimpleTracer()


def get_tracer():
    """Get tracer instance."""
    global _tracer

    if _tracer is None:
        if HAS_OPENTELEMETRY:
            # Initialize OpenTelemetry
            resource = Resource.create({"service.name": "neolight"})
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            trace.set_tracer_provider(provider)
            _tracer = trace.get_tracer(__name__)
        else:
            _tracer = _simple_tracer

    return _tracer


@contextmanager
def trace_operation(operation_name: str, **attributes):
    """Context manager for tracing operations."""
    tracer = get_tracer()

    if HAS_OPENTELEMETRY:
        span = tracer.start_span(operation_name)
        for key, value in attributes.items():
            span.set_attribute(key, str(value))
        try:
            yield span
            span.set_status(trace.Status(trace.StatusCode.OK))
        except Exception as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            span.end()
    else:
        # Simple tracer
        span_id = tracer.start_span(operation_name)
        for key, value in attributes.items():
            tracer.add_attribute(span_id, key, value)
        try:
            yield span_id
            tracer.end_span(span_id, status="OK")
        except Exception as e:
            tracer.end_span(span_id, status="ERROR", error=str(e))
            raise


def get_correlation_id() -> str:
    """Generate correlation ID for request tracking."""
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context (for propagation)."""
    # In a real implementation, this would use contextvars
    # For now, we'll use thread-local storage or pass it explicitly
    pass


# Import json for SimpleTracer
import json

