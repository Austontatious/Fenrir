from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from copy import deepcopy
import json
import re
from typing import Any, Sequence

from core.prompt_loader import PromptLoader
from fenrir.adapters.openai_compatible import OpenAICompatibleAdapter
from fenrir.generation.prompt_templates import build_prompt_bundle
from fenrir.generation.schemas import (
    SchemaValidationError,
    build_generation_schema,
    require_valid_batch,
)


class SeedGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SeedGenerationRequest:
    battery_id: str
    version: str
    family: str
    count: int
    generation_prompt_version: str
    dimension_ids: Sequence[str]
    coverage_ids: Sequence[str]
    pressure_ids: Sequence[str]
    sensitivity_ids: Sequence[str]


@dataclass
class SeedGenerationResult:
    batch: dict[str, Any]
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]
    raw_text: str
    prompt_name: str
    prompt_sha256: str
    prompt_version: str


FAMILY_ID_PREFIX = {
    "trait_forced_choice": "trait_fc",
    "sjt_seed": "sjt",
    "redteam_behavioral_probe": "rt_probe",
    "consistency_variant": "consistency",
}


class OpenAISeedGenerator:
    def __init__(
        self,
        *,
        adapter: OpenAICompatibleAdapter,
        prompt_loader: PromptLoader,
        seed_batch_schema: dict[str, Any],
        generator_model: str,
    ) -> None:
        self._adapter = adapter
        self._prompt_loader = prompt_loader
        self._seed_batch_schema = dict(seed_batch_schema)
        self._generator_model = generator_model

    def generate(
        self,
        request: SeedGenerationRequest,
        *,
        max_output_tokens: int,
        temperature: float | None,
        store: bool,
    ) -> SeedGenerationResult:
        prompt_bundle = build_prompt_bundle(
            prompt_loader=self._prompt_loader,
            family=request.family,
            count=request.count,
            battery_id=request.battery_id,
            version=request.version,
            generation_prompt_version=request.generation_prompt_version,
            dimension_ids=request.dimension_ids,
            coverage_ids=request.coverage_ids,
            pressure_ids=request.pressure_ids,
            sensitivity_ids=request.sensitivity_ids,
        )

        generation_schema = build_generation_schema(
            seed_batch_schema=self._seed_batch_schema,
            family=request.family,
            count=request.count,
            battery_id=request.battery_id,
            version=request.version,
            generation_prompt_version=request.generation_prompt_version,
            generator_model=self._generator_model,
        )

        response = self._adapter.generate_responses(
            system_prompt=prompt_bundle.system_text,
            user_prompt=prompt_bundle.user_text,
            json_schema=generation_schema,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            store=store,
        )
        if response.error_state:
            raise SeedGenerationError(response.error_state)

        parsed = self._parse_json(response.raw_response)
        if not isinstance(parsed, dict):
            raise SeedGenerationError("Structured output must decode to a JSON object")

        batch = self._normalize_batch(parsed, request)
        try:
            require_valid_batch(batch, self._seed_batch_schema)
        except SchemaValidationError as exc:
            raise SeedGenerationError(f"Generated batch failed schema validation: {exc}") from exc

        metadata = response.metadata or {}
        request_payload = metadata.get("request_payload")
        response_payload = metadata.get("raw")

        return SeedGenerationResult(
            batch=batch,
            request_payload=request_payload if isinstance(request_payload, dict) else {},
            response_payload=response_payload if isinstance(response_payload, dict) else {},
            raw_text=response.raw_response,
            prompt_name=prompt_bundle.prompt_name,
            prompt_sha256=prompt_bundle.prompt_sha256,
            prompt_version=prompt_bundle.prompt_version,
        )

    def _normalize_batch(
        self,
        payload: dict[str, Any],
        request: SeedGenerationRequest,
    ) -> dict[str, Any]:
        batch = deepcopy(payload)
        batch["battery_id"] = request.battery_id
        batch["version"] = request.version
        batch["generation_prompt_version"] = request.generation_prompt_version
        batch["generator_model"] = self._generator_model
        batch.setdefault("generated_at", utc_now_iso())

        items_raw = batch.get("items")
        if not isinstance(items_raw, list):
            raise SeedGenerationError("Batch payload missing items array")

        items: list[dict[str, Any]] = []
        for idx, item in enumerate(items_raw, start=1):
            if not isinstance(item, dict):
                raise SeedGenerationError(f"Item {idx} is not an object")
            normalized = deepcopy(item)
            normalized["battery_id"] = request.battery_id
            normalized["version"] = request.version
            normalized["family"] = request.family
            normalized["generation_prompt_version"] = request.generation_prompt_version
            normalized["generator_model"] = self._generator_model
            normalized.setdefault("review_status", "draft")
            normalized.setdefault("notes", "Draft seed generated for human review.")
            normalized.setdefault("variant_group", f"vg_{idx:03d}")
            normalized.setdefault("options", [])
            normalized["item_id"] = _canonical_item_id(
                normalized.get("item_id"),
                family=request.family,
                ordinal=idx,
            )
            items.append(normalized)

        seen_ids: set[str] = set()
        for idx, item in enumerate(items, start=1):
            item_id = item["item_id"]
            if item_id in seen_ids:
                item["item_id"] = _canonical_item_id(None, family=request.family, ordinal=idx)
            seen_ids.add(item["item_id"])

        batch["items"] = items
        return batch

    @staticmethod
    def _parse_json(raw_text: str) -> Any:
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text).strip()
            text = re.sub(r"```$", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))


def _canonical_item_id(raw_item_id: Any, *, family: str, ordinal: int) -> str:
    prefix = FAMILY_ID_PREFIX.get(family, "seed")
    if isinstance(raw_item_id, str) and raw_item_id.strip():
        cleaned = raw_item_id.strip().lower()
        cleaned = re.sub(r"[^a-z0-9_\-]", "_", cleaned)
        if cleaned:
            return cleaned
    return f"{prefix}_{ordinal:04d}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
