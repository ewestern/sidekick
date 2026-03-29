from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.agent_config_create_prompts import AgentConfigCreatePrompts


T = TypeVar("T", bound="AgentConfigCreate")


@_attrs_define
class AgentConfigCreate:
    """
    Attributes:
        model (str):
        prompts (AgentConfigCreatePrompts):
        id (None | str | Unset):
        agent_id (None | str | Unset):
        skills (list[str] | Unset):
        updated_by (None | str | Unset):
    """

    model: str
    prompts: AgentConfigCreatePrompts
    id: None | str | Unset = UNSET
    agent_id: None | str | Unset = UNSET
    skills: list[str] | Unset = UNSET
    updated_by: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        model = self.model

        prompts = self.prompts.to_dict()

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        agent_id: None | str | Unset
        if isinstance(self.agent_id, Unset):
            agent_id = UNSET
        else:
            agent_id = self.agent_id

        skills: list[str] | Unset = UNSET
        if not isinstance(self.skills, Unset):
            skills = self.skills

        updated_by: None | str | Unset
        if isinstance(self.updated_by, Unset):
            updated_by = UNSET
        else:
            updated_by = self.updated_by

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "model": model,
                "prompts": prompts,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if agent_id is not UNSET:
            field_dict["agent_id"] = agent_id
        if skills is not UNSET:
            field_dict["skills"] = skills
        if updated_by is not UNSET:
            field_dict["updated_by"] = updated_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.agent_config_create_prompts import AgentConfigCreatePrompts

        d = dict(src_dict)
        model = d.pop("model")

        prompts = AgentConfigCreatePrompts.from_dict(d.pop("prompts"))

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        def _parse_agent_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        agent_id = _parse_agent_id(d.pop("agent_id", UNSET))

        skills = cast(list[str], d.pop("skills", UNSET))

        def _parse_updated_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        updated_by = _parse_updated_by(d.pop("updated_by", UNSET))

        agent_config_create = cls(
            model=model,
            prompts=prompts,
            id=id,
            agent_id=agent_id,
            skills=skills,
            updated_by=updated_by,
        )

        agent_config_create.additional_properties = d
        return agent_config_create

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
