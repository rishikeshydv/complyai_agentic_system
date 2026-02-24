from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..db import LawRepository
from .models import ControlObjective, Event


@dataclass
class DeterministicMatch:
    control_ids: list[str]
    controls: list[ControlObjective]
    obligations_with_context: list[dict[str, Any]]


class DeterministicMapper:
    def __init__(self, repository: LawRepository):
        self.repository = repository

    def map_event(self, event: Event) -> DeterministicMatch | None:
        rule_map = self.repository.get_latest_rule_map(event.bank_id, event.rule_triggered)
        if not rule_map:
            return None

        typology = self.repository.get_typology(rule_map.typology_id)
        default_controls = typology.default_control_ids if typology else []
        control_ids = list(rule_map.control_ids or default_controls)
        if not control_ids:
            return None

        controls = self.repository.get_control_objectives(control_ids)
        if not controls:
            return None

        control_obligation_maps = self.repository.get_control_to_obligation_maps(
            control_ids=control_ids,
            jurisdiction_context=event.jurisdiction_context,
        )

        obligation_ids = []
        seen = set()
        for mapping in control_obligation_maps:
            for obligation_id in mapping.obligation_ids:
                if obligation_id in seen:
                    continue
                seen.add(obligation_id)
                obligation_ids.append(obligation_id)

        if not obligation_ids:
            return None

        obligations_with_context = self.repository.get_obligations_with_context(obligation_ids)
        if not obligations_with_context:
            return None

        return DeterministicMatch(
            control_ids=control_ids,
            controls=controls,
            obligations_with_context=obligations_with_context,
        )
