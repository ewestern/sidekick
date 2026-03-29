from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.source_patch_health_type_0 import SourcePatchHealthType0
    from ..models.source_patch_schedule_type_0 import SourcePatchScheduleType0


T = TypeVar("T", bound="SourcePatch")


@_attrs_define
class SourcePatch:
    """
    Attributes:
        name (None | str | Unset):
        endpoint (None | str | Unset):
        schedule (None | SourcePatchScheduleType0 | Unset):
        beat (None | str | Unset):
        geo (None | str | Unset):
        related_sources (list[str] | None | Unset):
        registered_at (datetime.datetime | None | Unset):
        health (None | SourcePatchHealthType0 | Unset):
        source_tier (None | str | Unset):
        outlet (None | str | Unset):
    """

    name: None | str | Unset = UNSET
    endpoint: None | str | Unset = UNSET
    schedule: None | SourcePatchScheduleType0 | Unset = UNSET
    beat: None | str | Unset = UNSET
    geo: None | str | Unset = UNSET
    related_sources: list[str] | None | Unset = UNSET
    registered_at: datetime.datetime | None | Unset = UNSET
    health: None | SourcePatchHealthType0 | Unset = UNSET
    source_tier: None | str | Unset = UNSET
    outlet: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.source_patch_health_type_0 import SourcePatchHealthType0
        from ..models.source_patch_schedule_type_0 import SourcePatchScheduleType0

        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        endpoint: None | str | Unset
        if isinstance(self.endpoint, Unset):
            endpoint = UNSET
        else:
            endpoint = self.endpoint

        schedule: dict[str, Any] | None | Unset
        if isinstance(self.schedule, Unset):
            schedule = UNSET
        elif isinstance(self.schedule, SourcePatchScheduleType0):
            schedule = self.schedule.to_dict()
        else:
            schedule = self.schedule

        beat: None | str | Unset
        if isinstance(self.beat, Unset):
            beat = UNSET
        else:
            beat = self.beat

        geo: None | str | Unset
        if isinstance(self.geo, Unset):
            geo = UNSET
        else:
            geo = self.geo

        related_sources: list[str] | None | Unset
        if isinstance(self.related_sources, Unset):
            related_sources = UNSET
        elif isinstance(self.related_sources, list):
            related_sources = self.related_sources

        else:
            related_sources = self.related_sources

        registered_at: None | str | Unset
        if isinstance(self.registered_at, Unset):
            registered_at = UNSET
        elif isinstance(self.registered_at, datetime.datetime):
            registered_at = self.registered_at.isoformat()
        else:
            registered_at = self.registered_at

        health: dict[str, Any] | None | Unset
        if isinstance(self.health, Unset):
            health = UNSET
        elif isinstance(self.health, SourcePatchHealthType0):
            health = self.health.to_dict()
        else:
            health = self.health

        source_tier: None | str | Unset
        if isinstance(self.source_tier, Unset):
            source_tier = UNSET
        else:
            source_tier = self.source_tier

        outlet: None | str | Unset
        if isinstance(self.outlet, Unset):
            outlet = UNSET
        else:
            outlet = self.outlet

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if endpoint is not UNSET:
            field_dict["endpoint"] = endpoint
        if schedule is not UNSET:
            field_dict["schedule"] = schedule
        if beat is not UNSET:
            field_dict["beat"] = beat
        if geo is not UNSET:
            field_dict["geo"] = geo
        if related_sources is not UNSET:
            field_dict["related_sources"] = related_sources
        if registered_at is not UNSET:
            field_dict["registered_at"] = registered_at
        if health is not UNSET:
            field_dict["health"] = health
        if source_tier is not UNSET:
            field_dict["source_tier"] = source_tier
        if outlet is not UNSET:
            field_dict["outlet"] = outlet

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.source_patch_health_type_0 import SourcePatchHealthType0
        from ..models.source_patch_schedule_type_0 import SourcePatchScheduleType0

        d = dict(src_dict)

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

        def _parse_endpoint(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        endpoint = _parse_endpoint(d.pop("endpoint", UNSET))

        def _parse_schedule(data: object) -> None | SourcePatchScheduleType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                schedule_type_0 = SourcePatchScheduleType0.from_dict(data)

                return schedule_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SourcePatchScheduleType0 | Unset, data)

        schedule = _parse_schedule(d.pop("schedule", UNSET))

        def _parse_beat(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        beat = _parse_beat(d.pop("beat", UNSET))

        def _parse_geo(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        geo = _parse_geo(d.pop("geo", UNSET))

        def _parse_related_sources(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                related_sources_type_0 = cast(list[str], data)

                return related_sources_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        related_sources = _parse_related_sources(d.pop("related_sources", UNSET))

        def _parse_registered_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                registered_at_type_0 = isoparse(data)

                return registered_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        registered_at = _parse_registered_at(d.pop("registered_at", UNSET))

        def _parse_health(data: object) -> None | SourcePatchHealthType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                health_type_0 = SourcePatchHealthType0.from_dict(data)

                return health_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | SourcePatchHealthType0 | Unset, data)

        health = _parse_health(d.pop("health", UNSET))

        def _parse_source_tier(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        source_tier = _parse_source_tier(d.pop("source_tier", UNSET))

        def _parse_outlet(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        outlet = _parse_outlet(d.pop("outlet", UNSET))

        source_patch = cls(
            name=name,
            endpoint=endpoint,
            schedule=schedule,
            beat=beat,
            geo=geo,
            related_sources=related_sources,
            registered_at=registered_at,
            health=health,
            source_tier=source_tier,
            outlet=outlet,
        )

        source_patch.additional_properties = d
        return source_patch

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
