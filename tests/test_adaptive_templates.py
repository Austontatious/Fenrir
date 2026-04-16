from __future__ import annotations

from fenrir.adaptive.schemas import ADAPTIVE_TEMPLATE_SCHEMA_VERSION
from fenrir.adaptive.templates import load_template_families


def test_adaptive_templates_load_and_respect_v0_bounds() -> None:
    templates = load_template_families()
    assert 3 <= len(templates) <= 5

    dimensions = {template.dimension for template in templates}
    assert 2 <= len(dimensions) <= 3

    template_ids = {template.template_id for template in templates}
    assert len(template_ids) == len(templates)

    for template in templates:
        assert template.schema_version == ADAPTIVE_TEMPLATE_SCHEMA_VERSION
        assert template.stable_option in {"A", "B"}
        assert template.pressure_option in {"A", "B"}
        assert template.stable_option != template.pressure_option

        level_ids = [level.level_id for level in template.ladder]
        assert level_ids == ["L1", "L2", "L3", "L4", "L5"]
