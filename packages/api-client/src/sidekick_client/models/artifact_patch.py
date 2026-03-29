from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.artifact_patch_entities_type_0_item import ArtifactPatchEntitiesType0Item


T = TypeVar("T", bound="ArtifactPatch")


@_attrs_define
class ArtifactPatch:
    """
    Attributes:
        media_type (None | str | Unset):
        event_group (None | str | Unset):
        beat (None | str | Unset):
        geo (None | str | Unset):
        period_start (datetime.date | None | Unset):
        period_end (datetime.date | None | Unset):
        assignment_id (None | str | Unset):
        story_key (None | str | Unset):
        entities (list[ArtifactPatchEntitiesType0Item] | None | Unset):
        topics (list[str] | None | Unset):
        status (None | str | Unset):
        superseded_by (None | str | Unset):
    """

    media_type: None | str | Unset = UNSET
    event_group: None | str | Unset = UNSET
    beat: None | str | Unset = UNSET
    geo: None | str | Unset = UNSET
    period_start: datetime.date | None | Unset = UNSET
    period_end: datetime.date | None | Unset = UNSET
    assignment_id: None | str | Unset = UNSET
    story_key: None | str | Unset = UNSET
    entities: list[ArtifactPatchEntitiesType0Item] | None | Unset = UNSET
    topics: list[str] | None | Unset = UNSET
    status: None | str | Unset = UNSET
    superseded_by: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        media_type: None | str | Unset
        if isinstance(self.media_type, Unset):
            media_type = UNSET
        else:
            media_type = self.media_type

        event_group: None | str | Unset
        if isinstance(self.event_group, Unset):
            event_group = UNSET
        else:
            event_group = self.event_group

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

        period_start: None | str | Unset
        if isinstance(self.period_start, Unset):
            period_start = UNSET
        elif isinstance(self.period_start, datetime.date):
            period_start = self.period_start.isoformat()
        else:
            period_start = self.period_start

        period_end: None | str | Unset
        if isinstance(self.period_end, Unset):
            period_end = UNSET
        elif isinstance(self.period_end, datetime.date):
            period_end = self.period_end.isoformat()
        else:
            period_end = self.period_end

        assignment_id: None | str | Unset
        if isinstance(self.assignment_id, Unset):
            assignment_id = UNSET
        else:
            assignment_id = self.assignment_id

        story_key: None | str | Unset
        if isinstance(self.story_key, Unset):
            story_key = UNSET
        else:
            story_key = self.story_key

        entities: list[dict[str, Any]] | None | Unset
        if isinstance(self.entities, Unset):
            entities = UNSET
        elif isinstance(self.entities, list):
            entities = []
            for entities_type_0_item_data in self.entities:
                entities_type_0_item = entities_type_0_item_data.to_dict()
                entities.append(entities_type_0_item)

        else:
            entities = self.entities

        topics: list[str] | None | Unset
        if isinstance(self.topics, Unset):
            topics = UNSET
        elif isinstance(self.topics, list):
            topics = self.topics

        else:
            topics = self.topics

        status: None | str | Unset
        if isinstance(self.status, Unset):
            status = UNSET
        else:
            status = self.status

        superseded_by: None | str | Unset
        if isinstance(self.superseded_by, Unset):
            superseded_by = UNSET
        else:
            superseded_by = self.superseded_by

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if media_type is not UNSET:
            field_dict["media_type"] = media_type
        if event_group is not UNSET:
            field_dict["event_group"] = event_group
        if beat is not UNSET:
            field_dict["beat"] = beat
        if geo is not UNSET:
            field_dict["geo"] = geo
        if period_start is not UNSET:
            field_dict["period_start"] = period_start
        if period_end is not UNSET:
            field_dict["period_end"] = period_end
        if assignment_id is not UNSET:
            field_dict["assignment_id"] = assignment_id
        if story_key is not UNSET:
            field_dict["story_key"] = story_key
        if entities is not UNSET:
            field_dict["entities"] = entities
        if topics is not UNSET:
            field_dict["topics"] = topics
        if status is not UNSET:
            field_dict["status"] = status
        if superseded_by is not UNSET:
            field_dict["superseded_by"] = superseded_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.artifact_patch_entities_type_0_item import ArtifactPatchEntitiesType0Item

        d = dict(src_dict)

        def _parse_media_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        media_type = _parse_media_type(d.pop("media_type", UNSET))

        def _parse_event_group(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        event_group = _parse_event_group(d.pop("event_group", UNSET))

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

        def _parse_period_start(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                period_start_type_0 = isoparse(data).date()

                return period_start_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        period_start = _parse_period_start(d.pop("period_start", UNSET))

        def _parse_period_end(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                period_end_type_0 = isoparse(data).date()

                return period_end_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        period_end = _parse_period_end(d.pop("period_end", UNSET))

        def _parse_assignment_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        assignment_id = _parse_assignment_id(d.pop("assignment_id", UNSET))

        def _parse_story_key(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        story_key = _parse_story_key(d.pop("story_key", UNSET))

        def _parse_entities(data: object) -> list[ArtifactPatchEntitiesType0Item] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                entities_type_0 = []
                _entities_type_0 = data
                for entities_type_0_item_data in _entities_type_0:
                    entities_type_0_item = ArtifactPatchEntitiesType0Item.from_dict(entities_type_0_item_data)

                    entities_type_0.append(entities_type_0_item)

                return entities_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[ArtifactPatchEntitiesType0Item] | None | Unset, data)

        entities = _parse_entities(d.pop("entities", UNSET))

        def _parse_topics(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                topics_type_0 = cast(list[str], data)

                return topics_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        topics = _parse_topics(d.pop("topics", UNSET))

        def _parse_status(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        status = _parse_status(d.pop("status", UNSET))

        def _parse_superseded_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        superseded_by = _parse_superseded_by(d.pop("superseded_by", UNSET))

        artifact_patch = cls(
            media_type=media_type,
            event_group=event_group,
            beat=beat,
            geo=geo,
            period_start=period_start,
            period_end=period_end,
            assignment_id=assignment_id,
            story_key=story_key,
            entities=entities,
            topics=topics,
            status=status,
            superseded_by=superseded_by,
        )

        artifact_patch.additional_properties = d
        return artifact_patch

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
