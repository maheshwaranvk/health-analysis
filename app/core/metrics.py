"""
Simple observability / metrics module.

Tracks request counts, latency, LLM calls, and safety violations
using in-memory counters.  Exposed via GET /metrics.
"""

import threading
import time
from dataclasses import dataclass, field


@dataclass
class AppMetrics:
    """Thread-safe in-memory metrics counters."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    total_requests: int = 0
    analysis_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    llm_calls: int = 0
    safety_violations: int = 0

    # Latency tracking (seconds)
    _latencies: list[float] = field(default_factory=list, repr=False)

    # ── Recording helpers ────────────────────────────────────────────
    def record_request(self) -> None:
        with self._lock:
            self.total_requests += 1

    def record_analysis(self) -> None:
        with self._lock:
            self.analysis_requests += 1

    def record_success(self) -> None:
        with self._lock:
            self.successful_requests += 1

    def record_failure(self) -> None:
        with self._lock:
            self.failed_requests += 1

    def record_llm_call(self) -> None:
        with self._lock:
            self.llm_calls += 1

    def record_safety_violation(self) -> None:
        with self._lock:
            self.safety_violations += 1

    def record_latency(self, seconds: float) -> None:
        with self._lock:
            self._latencies.append(seconds)

    # ── Getters ──────────────────────────────────────────────────────
    def avg_latency_ms(self) -> float:
        with self._lock:
            if not self._latencies:
                return 0.0
            return (sum(self._latencies) / len(self._latencies)) * 1000

    def last_latency_ms(self) -> float:
        with self._lock:
            return (self._latencies[-1] * 1000) if self._latencies else 0.0

    def snapshot(self) -> dict:
        """Return a plain-dict snapshot of current metrics."""
        with self._lock:
            return {
                "total_requests": self.total_requests,
                "analysis_requests": self.analysis_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "llm_calls": self.llm_calls,
                "safety_violations": self.safety_violations,
                "avg_latency_ms": round(self.avg_latency_ms(), 2),
                "last_latency_ms": round(self.last_latency_ms(), 2),
            }


# Module-level singleton
metrics = AppMetrics()
