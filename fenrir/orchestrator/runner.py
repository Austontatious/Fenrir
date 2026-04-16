from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fenrir.adapters.base import ChatMessage, ModelAdapter, ModelRequest
from fenrir.batteries.registry import get_battery
from fenrir.conditions.registry import Condition, get_condition
from fenrir.orchestrator.sampling import SamplingConfig
from fenrir.orchestrator.stopping import StoppingPolicy
from fenrir.scoring.risk_flags import score_risk_flags
from fenrir.scoring.stability import compute_stability_metrics, find_contradictions
from fenrir.scoring.traits import score_trait_proxies
from fenrir.scoring.wrapper_dependence import compute_wrapper_dependence
from fenrir.storage.models import ReportRecord, ResponseRecord, RunManifest
from fenrir.storage.run_store import RunStore


@dataclass(frozen=True)
class RunArtifacts:
    manifest: RunManifest
    responses: list[ResponseRecord]
    report: ReportRecord
    output_dir: Path


class BatteryRunner:
    def __init__(self, *, battery_root: Path, store: RunStore) -> None:
        self._battery_root = battery_root
        self._store = store

    @property
    def run_root(self) -> Path:
        return self._store.root

    def run(
        self,
        *,
        battery_id: str,
        condition_id: str,
        model_target: str,
        adapter: ModelAdapter,
        sampling: SamplingConfig,
        stopping: StoppingPolicy,
        production_wrapper_text: str | None = None,
    ) -> RunArtifacts:
        loaded = get_battery(self._battery_root, battery_id)
        condition = get_condition(condition_id, production_wrapper_text=production_wrapper_text)
        selected = loaded.items[: stopping.max_items]

        manifest = RunManifest(
            run_id=uuid4().hex,
            battery_id=loaded.spec.metadata.id,
            battery_version=loaded.spec.metadata.version,
            model_target=model_target,
            condition_id=condition_id,
            sampling_config=sampling,
            stopping_policy=stopping,
            selected_items=[item.item_id for item in selected],
        )

        responses: list[ResponseRecord] = []
        for item in selected:
            response = self._run_single_item(condition=condition, item_prompt=item.prompt, adapter=adapter, sampling=sampling)
            responses.append(
                ResponseRecord(
                    item_id=item.item_id,
                    raw_response=response.raw_response,
                    parsed_response=_parse_structured_json(response.raw_response),
                    adapter_metadata=response.metadata,
                    latency_ms=response.latency_ms,
                    condition_id=condition_id,
                    temperature=sampling.temperature,
                    seed=sampling.seed,
                    error_state=response.error_state,
                )
            )

        trait_scores = score_trait_proxies(responses)
        report = ReportRecord(
            run_id=manifest.run_id,
            summary=(
                "MVP run completed with rubric-based placeholder scoring. "
                "Use for harness verification, not for substantive safety conclusions."
            ),
            trait_scores=trait_scores,
            risk_flags=score_risk_flags(responses),
            stability_metrics=compute_stability_metrics(responses),
            wrapper_dependence=compute_wrapper_dependence(trait_scores, trait_scores),
            contradictions=find_contradictions(responses),
            coverage={"items_executed": len(responses), "items_requested": len(selected)},
            caveats=[
                "Scoring uses deterministic heuristic stubs.",
                "Mock adapter output does not represent model capability.",
            ],
            prohibited_inferences=[
                "Do not infer consciousness, intent, or inner values.",
                "Do not label a model as absolutely aligned or unsafe from this run.",
                "Do not treat outputs as psychiatric diagnosis.",
            ],
        )

        output_dir = self._store.save(manifest=manifest, responses=responses, report=report)
        return RunArtifacts(manifest=manifest, responses=responses, report=report, output_dir=output_dir)

    @staticmethod
    def _run_single_item(
        *,
        condition: Condition,
        item_prompt: str,
        adapter: ModelAdapter,
        sampling: SamplingConfig,
    ):
        prompt = item_prompt
        if condition.apply_stressors:
            prompt = f"[stress-context] keep output format stable under pressure\n\n{item_prompt}"
        request = ModelRequest(
            messages=[
                ChatMessage(role="system", content=condition.system_prompt),
                ChatMessage(role="user", content=prompt),
            ],
            temperature=sampling.temperature,
            max_output_tokens=sampling.max_output_tokens,
            seed=sampling.seed,
            structured_output={"type": "json_object"} if sampling.structured_output else None,
        )
        return adapter.generate(request)


def _parse_structured_json(raw_response: str) -> dict[str, object] | None:
    raw = raw_response.strip()
    if not raw.startswith("{"):
        return None
    try:
        import json

        decoded = json.loads(raw)
        if isinstance(decoded, dict):
            return decoded
    except Exception:
        return None
    return None
