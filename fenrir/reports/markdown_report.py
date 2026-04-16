from __future__ import annotations

from fenrir.storage.models import ReportRecord


def render_markdown_report(report: ReportRecord) -> str:
    lines: list[str] = []
    lines.append(f"# Fenrir Report: {report.run_id}")
    lines.append("")
    lines.append("## Summary")
    lines.append(report.summary)
    lines.append("")
    lines.append("## Trait Scores")
    for key, value in sorted(report.trait_scores.items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Risk Flags")
    for key, value in sorted(report.risk_flags.items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Stability Metrics")
    for key, value in sorted(report.stability_metrics.items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Wrapper Dependence")
    for key, value in sorted(report.wrapper_dependence.items()):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Contradictions")
    if report.contradictions:
        for item in report.contradictions:
            lines.append(f"- {item}")
    else:
        lines.append("- none observed")
    lines.append("")
    lines.append("## Caveats")
    for caveat in report.caveats:
        lines.append(f"- {caveat}")
    lines.append("")
    lines.append("## Prohibited Inferences")
    for item in report.prohibited_inferences:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)
