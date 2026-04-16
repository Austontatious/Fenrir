from __future__ import annotations

from fenrir.storage.models import ReportRecord


def render_markdown_report(report: ReportRecord) -> str:
    lines: list[str] = []
    lines.append(f"# Fenrir Report: {report.run_id}")
    lines.append("")
    lines.append(f"- Report schema: `{report.schema_version}`")
    lines.append(f"- Report version: `{report.report_version}`")
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
    lines.append(f"- index: {report.wrapper_dependence.index}")
    lines.append(f"- bucket: {report.wrapper_dependence.bucket}")
    lines.append(f"- explanation: {report.wrapper_dependence.explanation}")
    if report.wrapper_dependence.pair_deltas:
        for key, value in sorted(report.wrapper_dependence.pair_deltas.items()):
            lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Condition Provenance")
    condition = report.condition_provenance
    lines.append(f"- condition_id: {condition.condition_id}")
    lines.append(f"- condition_version: {condition.condition_version}")
    lines.append(f"- system_prompt_source: {condition.system_prompt_source}")
    lines.append(f"- system_prompt_hash: {condition.system_prompt_hash}")
    lines.append(f"- prompt_template_version: {condition.prompt_template_version}")
    lines.append(f"- inline_prompt_hash: {condition.inline_prompt_hash}")
    lines.append(f"- stress_profile_id: {condition.stress_profile_id}")
    lines.append(f"- stress_profile_version: {condition.stress_profile_version}")
    lines.append(f"- production_wrapper_source: {condition.production_wrapper_source}")
    lines.append("")

    lines.append("## Contradictions")
    if report.contradictions:
        for item in report.contradictions:
            lines.append(f"- {item}")
    else:
        lines.append("- none observed")
    lines.append("")

    lines.append("## Coverage")
    for key, value in sorted(report.coverage.items()):
        lines.append(f"- {key}: {value}")
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
