"""Performance monitoring utilities for the ablation framework."""

import functools
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a function or block of code."""

    name: str
    start_time: datetime
    end_time: datetime | None = None
    execution_time_ms: float | None = None
    cpu_percent: float | None = None
    memory_usage_mb: float | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the metrics to a dictionary.

        Returns:
            Dict[str, Any]: The metrics as a dictionary.
        """
        result = {
            "name": self.name,
            "start_time": self.start_time.isoformat(),
            "context": self.context,
        }

        if self.end_time:
            result["end_time"] = self.end_time.isoformat()

        if self.execution_time_ms is not None:
            result["execution_time_ms"] = self.execution_time_ms

        if self.cpu_percent is not None:
            result["cpu_percent"] = self.cpu_percent

        if self.memory_usage_mb is not None:
            result["memory_usage_mb"] = self.memory_usage_mb

        return result


class PerformanceMonitor:
    """Performance monitor for the ablation framework.

    This class provides utilities for monitoring the performance of
    functions and blocks of code.
    """

    def __init__(self):
        """Initialize the performance monitor."""
        self.metrics: list[PerformanceMetrics] = []
        self.current_metrics: dict[str, PerformanceMetrics] = {}

    def start_timer(self, name: str, context: dict[str, Any] | None = None) -> PerformanceMetrics:
        """Start a timer.

        Args:
            name: The name of the timer.
            context: Optional context for the timer.

        Returns:
            PerformanceMetrics: The metrics object.
        """
        # Create metrics
        metrics = PerformanceMetrics(
            name=name,
            start_time=datetime.now(UTC),
            context=context or {},
        )

        # Store metrics
        self.current_metrics[name] = metrics

        return metrics

    def stop_timer(self, name: str) -> PerformanceMetrics | None:
        """Stop a timer.

        Args:
            name: The name of the timer.

        Returns:
            Optional[PerformanceMetrics]: The metrics object, or None if the timer wasn't found.
        """
        # Get metrics
        metrics = self.current_metrics.get(name)
        if not metrics:
            logger.warning(f"Timer '{name}' not found")
            return None

        # Update metrics
        metrics.end_time = datetime.now(UTC)
        metrics.execution_time_ms = (metrics.end_time - metrics.start_time).total_seconds() * 1000
        metrics.cpu_percent = psutil.cpu_percent()
        metrics.memory_usage_mb = psutil.Process().memory_info().rss / (1024 * 1024)

        # Remove from current metrics
        self.current_metrics.pop(name)

        # Add to metrics list
        self.metrics.append(metrics)

        return metrics

    def get_metrics(self) -> list[PerformanceMetrics]:
        """Get all recorded metrics.

        Returns:
            List[PerformanceMetrics]: The metrics.
        """
        return self.metrics.copy()

    def get_metrics_for_name(self, name: str) -> list[PerformanceMetrics]:
        """Get metrics for a specific name.

        Args:
            name: The name to filter by.

        Returns:
            List[PerformanceMetrics]: The metrics for the name.
        """
        return [m for m in self.metrics if m.name == name]

    def get_metrics_for_context(self, context_key: str, context_value: Any) -> list[PerformanceMetrics]:
        """Get metrics for a specific context key and value.

        Args:
            context_key: The context key to filter by.
            context_value: The context value to filter by.

        Returns:
            List[PerformanceMetrics]: The metrics for the context key and value.
        """
        return [m for m in self.metrics if m.context.get(context_key) == context_value]

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()

    def summarize_metrics(self) -> dict[str, dict[str, float]]:
        """Summarize metrics by name.

        Returns:
            Dict[str, Dict[str, float]]: Summary of metrics by name.
        """
        summary = {}

        for name in set(m.name for m in self.metrics):
            metrics = self.get_metrics_for_name(name)
            execution_times = [m.execution_time_ms for m in metrics if m.execution_time_ms is not None]
            cpu_percents = [m.cpu_percent for m in metrics if m.cpu_percent is not None]
            memory_usages = [m.memory_usage_mb for m in metrics if m.memory_usage_mb is not None]

            summary[name] = {
                "count": len(metrics),
                "avg_execution_time_ms": sum(execution_times) / len(execution_times) if execution_times else 0,
                "min_execution_time_ms": min(execution_times) if execution_times else 0,
                "max_execution_time_ms": max(execution_times) if execution_times else 0,
                "avg_cpu_percent": sum(cpu_percents) / len(cpu_percents) if cpu_percents else 0,
                "avg_memory_usage_mb": sum(memory_usages) / len(memory_usages) if memory_usages else 0,
            }

        return summary

    @contextmanager
    def measure(self, name: str, context: dict[str, Any] | None = None):
        """Context manager for measuring performance.

        Args:
            name: The name of the measurement.
            context: Optional context for the measurement.

        Yields:
            None
        """
        self.start_timer(name, context)
        try:
            yield
        finally:
            self.stop_timer(name)

    def measure_function(self, name: str | None = None, context: dict[str, Any] | None = None):
        """Decorator for measuring function performance.

        Args:
            name: The name of the measurement. If not provided, the function name will be used.
            context: Optional context for the measurement.

        Returns:
            callable: The decorated function.
        """

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                measurement_name = name or func.__name__
                measurement_context = context or {}

                with self.measure(measurement_name, measurement_context):
                    return func(*args, **kwargs)

            return wrapper

        return decorator


# Global performance monitor
_global_perf_monitor = PerformanceMonitor()


def get_global_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor.

    Returns:
        PerformanceMonitor: The global performance monitor.
    """
    return _global_perf_monitor


def measure(name: str, context: dict[str, Any] | None = None):
    """Context manager for measuring performance.

    Args:
        name: The name of the measurement.
        context: Optional context for the measurement.

    Returns:
        contextmanager: The context manager.
    """
    return _global_perf_monitor.measure(name, context)


def measure_function(name: str | None = None, context: dict[str, Any] | None = None):
    """Decorator for measuring function performance.

    Args:
        name: The name of the measurement. If not provided, the function name will be used.
        context: Optional context for the measurement.

    Returns:
        callable: The decorator.
    """
    return _global_perf_monitor.measure_function(name, context)


def get_metrics() -> list[PerformanceMetrics]:
    """Get all recorded metrics.

    Returns:
        List[PerformanceMetrics]: The metrics.
    """
    return _global_perf_monitor.get_metrics()


def get_metrics_for_name(name: str) -> list[PerformanceMetrics]:
    """Get metrics for a specific name.

    Args:
        name: The name to filter by.

    Returns:
        List[PerformanceMetrics]: The metrics for the name.
    """
    return _global_perf_monitor.get_metrics_for_name(name)


def summarize_metrics() -> dict[str, dict[str, float]]:
    """Summarize metrics by name.

    Returns:
        Dict[str, Dict[str, float]]: Summary of metrics by name.
    """
    return _global_perf_monitor.summarize_metrics()


def clear_metrics() -> None:
    """Clear all metrics."""
    _global_perf_monitor.clear_metrics()
