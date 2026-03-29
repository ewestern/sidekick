from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.agent_config_prompts import AgentConfigPrompts


T = TypeVar("T", bound="AgentConfig")


@_attrs_define
class AgentConfig:
    """Runtime configuration for a named agent — model and prompt definitions.

    A row must exist before an agent can be invoked. There are no code-level
    defaults; agents raise KeyError if no row is found.

    agent_id examples:
        "ingestion-worker"
        "processor:summary"
        "beat-agent:city-council:springfield-il"
        "editor-agent"

    prompts keys are agent-specific slot names, e.g.:
        {"system": "...", "analyze_template": "..."}

        Attributes:
            id (str):
            agent_id (str):
            model (str):
            prompts (AgentConfigPrompts):
            skills (list[str] | Unset):
            updated_at (datetime.datetime | Unset):
            updated_by (None | str | Unset):
    """

    id: str
    agent_id: str
    model: str
    prompts: AgentConfigPrompts
    skills: list[str] | Unset = UNSET
    updated_at: datetime.datetime | Unset = UNSET
    updated_by: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        agent_id = self.agent_id

        model = self.model

        prompts = self.prompts.to_dict()

        skills: list[str] | Unset = UNSET
        if not isinstance(self.skills, Unset):
            skills = self.skills

        updated_at: str | Unset = UNSET
        if not isinstance(self.updated_at, Unset):
            updated_at = self.updated_at.isoformat()

        updated_by: None | str | Unset
        if isinstance(self.updated_by, Unset):
            updated_by = UNSET
        else:
            updated_by = self.updated_by

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "agent_id": agent_id,
                "model": model,
                "prompts": prompts,
            }
        )
        if skills is not UNSET:
            field_dict["skills"] = skills
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at
        if updated_by is not UNSET:
            field_dict["updated_by"] = updated_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.agent_config_prompts import AgentConfigPrompts

        d = dict(src_dict)
        id = d.pop("id")

        agent_id = d.pop("agent_id")

        model = d.pop("model")

        prompts = AgentConfigPrompts.from_dict(d.pop("prompts"))

        skills = cast(list[str], d.pop("skills", UNSET))

        _updated_at = d.pop("updated_at", UNSET)
        updated_at: datetime.datetime | Unset
        if isinstance(_updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = isoparse(_updated_at)

        def _parse_updated_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        updated_by = _parse_updated_by(d.pop("updated_by", UNSET))

        agent_config = cls(
            id=id,
            agent_id=agent_id,
            model=model,
            prompts=prompts,
            skills=skills,
            updated_at=updated_at,
            updated_by=updated_by,
        )

        agent_config.additional_properties = d
        return agent_config

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
