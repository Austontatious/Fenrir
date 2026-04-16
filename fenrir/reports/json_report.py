from __future__ import annotations

from fenrir.storage.models import ReportRecord


def to_jsonable_report(report: ReportRecord) -> dict[str, object]:
    return report.model_dump()
