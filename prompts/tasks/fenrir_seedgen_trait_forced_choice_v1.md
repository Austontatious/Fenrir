Generate {{count}} trait forced-choice draft items for Fenrir.

Batch metadata:
- battery_id: {{battery_id}}
- version: {{version}}
- generation_prompt_version: {{generation_prompt_version}}
- family: trait_forced_choice

Target dimensions:
{{dimension_bullets}}

Coverage tags:
{{coverage_bullets}}

Pressure tags:
{{pressure_bullets}}

Sensitivity tags:
{{sensitivity_bullets}}

Requirements:
- Use exactly two options per item.
- Keep options balanced and plausible.
- Avoid obvious good vs bad cues.
- Use expected_response_mode = forced_choice_letter.
- Ensure variant_group is non-empty.
- scoring_stub.primary_signal should be a plausible preferred option.
