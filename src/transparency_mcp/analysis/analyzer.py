"""Analysis layer: pure use cases over domain ``Dataset``/``Record``.

No I/O here. The MCP tools call these services, which operate entirely on
in-memory ``Dataset`` objects. This keeps the analysis logic trivially
testable and reusable outside the MCP context.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..domain.enums import Metric
from ..domain.models import AnalysisResult, Dataset, Record


class AnalysisService:
    """Stateless service computing aggregate metrics over a ``Dataset``.

    Following the Single Responsibility Principle, this class only computes
    metrics — it does not fetch data (that's the fetchers' job) nor speak MCP
    (that's the delivery layer's job).
    """

    def analyze(
        self,
        dataset: Dataset,
        metric: Metric | str,
        field: str,
        *,
        by: str | None = None,
        top_n: int = 10,
    ) -> AnalysisResult:
        metric = Metric(metric)
        records = dataset.records
        if metric is Metric.TOP_N:
            return self._top_n(records, field, by, top_n)
        if metric is Metric.SUM:
            return self._sum(records, field, by)
        if metric is Metric.AVERAGE:
            return self._average(records, field, by)
        if metric is Metric.COUNT:
            return self._count(records, field, by)
        if metric is Metric.TREND:
            return self._trend(records, field, by)
        raise ValueError(f"Unsupported metric: {metric!r}")

    # -- metric implementations -------------------------------------------

    def _top_n(
        self, records: list[Record], field: str, by: str | None, top_n: int
    ) -> AnalysisResult:
        key_fn = _make_key_fn(by)
        bucket: dict[str, float] = defaultdict(float)
        for r in records:
            val = _read(r, field)
            if val is None:
                continue
            bucket[key_fn(r)] += val
        ranked = sorted(bucket.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
        return AnalysisResult(
            metric=Metric.TOP_N.value,
            field=field,
            by=by,
            total_records=len(records),
            result=[{"key": k, "value": v} for k, v in ranked],
            notes=f"Top {top_n} by {field}" + (f" grouped by {by}" if by else ""),
        )

    def _sum(self, records: list[Record], field: str, by: str | None) -> AnalysisResult:
        key_fn = _make_key_fn(by)
        bucket: dict[str, float] = defaultdict(float)
        for r in records:
            val = _read(r, field)
            if val is None:
                continue
            bucket[key_fn(r)] += val
        if by:
            result: Any = dict(sorted(bucket.items()))
        else:
            result = sum(bucket.values())
        return AnalysisResult(
            metric=Metric.SUM.value, field=field, by=by, total_records=len(records), result=result
        )

    def _average(self, records: list[Record], field: str, by: str | None) -> AnalysisResult:
        key_fn = _make_key_fn(by)
        totals: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)
        for r in records:
            val = _read(r, field)
            if val is None:
                continue
            k = key_fn(r)
            totals[k] += val
            counts[k] += 1
        if by:
            result = {k: totals[k] / counts[k] for k in totals if counts[k]}
        else:
            total = sum(totals.values())
            count = sum(counts.values())
            result = total / count if count else 0.0
        return AnalysisResult(
            metric=Metric.AVERAGE.value,
            field=field,
            by=by,
            total_records=len(records),
            result=result,
        )

    def _count(self, records: list[Record], field: str, by: str | None) -> AnalysisResult:
        if by:
            key_fn = _make_key_fn(by)
            bucket: dict[str, int] = defaultdict(int)
            for r in records:
                bucket[key_fn(r)] += 1
            result: Any = dict(sorted(bucket.items()))
        else:
            result = len(records)
        return AnalysisResult(
            metric=Metric.COUNT.value, field=field, by=by, total_records=len(records), result=result
        )

    def _trend(self, records: list[Record], field: str, by: str | None) -> AnalysisResult:
        dated = [r for r in records if r.date is not None]
        dated.sort(key=lambda r: (r.date, _read(r, field) or 0.0))
        points = [
            {
                "date": r.date.isoformat() if r.date else None,
                "key": _make_key_fn(by)(r) if by else None,
                "value": _read(r, field),
            }
            for r in dated
            if _read(r, field) is not None
        ]
        return AnalysisResult(
            metric=Metric.TREND.value, field=field, by=by, total_records=len(records), result=points
        )


# -- helpers ------------------------------------------------------------------


def _read(record: Record, field: str) -> float | None:
    """Read a numeric value from a Record.

    First checks the common ``Record.value`` if ``field`` is the record's
    ``value_label`` or the literal ``"value"``; otherwise looks up ``field``
    in ``record.fields`` and coerces to float.
    """
    if field == "value" or (record.value_label and field == record.value_label):
        return record.value
    raw = record.fields.get(field)
    if raw is None or raw == "":
        return None
    try:
        f = float(raw)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # NaN guard


def _make_key_fn(by: str | None):
    if not by:
        return lambda _r: "all"
    return lambda r: str(
        r.fields.get(by)
        or (r.entity if by == "entity" else None)
        or (r.date.isoformat() if by == "date" and r.date else None)
        or ""
    )


# Re-exported so callers don't need to import the class directly.
analysis_service = AnalysisService()
