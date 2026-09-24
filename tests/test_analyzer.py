"""Tests for the AnalysisService metric implementations (pure, no I/O)."""

from __future__ import annotations

from datetime import date

import pytest

from transparency_mcp.analysis import AnalysisService
from transparency_mcp.domain.enums import Country, Metric, RecordKind
from transparency_mcp.domain.models import Dataset, Record


def _rec(entity: str, value: float, **fields) -> Record:
    return Record(
        source="t",
        kind=RecordKind.SPENDING,
        country=Country.US,
        entity=entity,
        value=value,
        value_label="outlay_amount",
        fields={"entity": entity, "outlay_amount": value, **fields},
    )


@pytest.fixture
def dataset() -> Dataset:
    records = [
        _rec("A", 100.0, agency_name="A"),
        _rec("B", 300.0, agency_name="B"),
        _rec("A", 50.0, agency_name="A"),
        _rec("C", 75.0, agency_name="C"),
    ]
    return Dataset(source="t", records=records)


def test_sum_grouped_by(dataset):
    res = AnalysisService().analyze(dataset, Metric.SUM, "outlay_amount", by="agency_name")
    assert res.metric == "sum"
    assert res.result == {"A": 150.0, "B": 300.0, "C": 75.0}


def test_sum_ungrouped(dataset):
    res = AnalysisService().analyze(dataset, Metric.SUM, "outlay_amount")
    assert res.result == pytest.approx(525.0)


def test_average_grouped(dataset):
    res = AnalysisService().analyze(dataset, Metric.AVERAGE, "outlay_amount", by="agency_name")
    assert res.result == {"A": 75.0, "B": 300.0, "C": 75.0}


def test_count_grouped(dataset):
    res = AnalysisService().analyze(dataset, Metric.COUNT, "outlay_amount", by="agency_name")
    assert res.result == {"A": 2, "B": 1, "C": 1}


def test_count_ungrouped(dataset):
    res = AnalysisService().analyze(dataset, Metric.COUNT, "outlay_amount")
    assert res.result == 4


def test_top_n(dataset):
    res = AnalysisService().analyze(
        dataset, Metric.TOP_N, "outlay_amount", by="agency_name", top_n=2
    )
    assert res.result == [
        {"key": "B", "value": 300.0},
        {"key": "A", "value": 150.0},
    ]


def test_trend_uses_dates():
    records = [
        Record(
            source="t",
            kind=RecordKind.DEBT,
            country=Country.US,
            entity="US",
            value=1.0,
            value_label="v",
            date=date(2024, 1, 3),
            fields={"v": 1.0},
        ),
        Record(
            source="t",
            kind=RecordKind.DEBT,
            country=Country.US,
            entity="US",
            value=2.0,
            value_label="v",
            date=date(2024, 1, 2),
            fields={"v": 2.0},
        ),
        Record(
            source="t",
            kind=RecordKind.DEBT,
            country=Country.US,
            entity="US",
            value=None,
            value_label="v",
            date=date(2024, 1, 1),
            fields={"v": None},
        ),
    ]
    ds = Dataset(source="t", records=records)
    res = AnalysisService().analyze(ds, Metric.TREND, "v")
    # Sorted ascending by date; the None-valued record is dropped.
    assert [p["date"] for p in res.result] == ["2024-01-02", "2024-01-03"]
    assert [p["value"] for p in res.result] == [2.0, 1.0]


def test_invalid_metric_raises(dataset):
    with pytest.raises(ValueError, match="Metric"):
        AnalysisService().analyze(dataset, "bogus", "outlay_amount")


def test_value_field_uses_normalized_value(dataset):
    res = AnalysisService().analyze(dataset, Metric.SUM, "value")
    assert res.result == pytest.approx(525.0)
