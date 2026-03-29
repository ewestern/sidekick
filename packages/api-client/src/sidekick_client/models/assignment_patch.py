from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.assignment_patch_monitor_type_0 import AssignmentPatchMonitorType0
    from ..models.assignment_patch_query_params_type_0 import AssignmentPatchQueryParamsType0


T = TypeVar("T", bound="AssignmentPatch")


@_attrs_define
class AssignmentPatch:
    """
    Attributes:
        type_ (None | str | Unset):
        status (None | str | Unset):
        query_text (None | str | Unset):
        query_params (AssignmentPatchQueryParamsType0 | None | Unset):
        triggered_by (None | str | Unset):
        triggered_by_id (None | str | Unset):
        triggered_at (datetime.datetime | None | Unset):
        parent_assignment (None | str | Unset):
        artifacts_in (list[str] | None | Unset):
        artifacts_out (list[str] | None | Unset):
        sub_assignments (list[str] | None | Unset):
        monitor (AssignmentPatchMonitorType0 | None | Unset):
    """

    type_: None | str | Unset = UNSET
    status: None | str | Unset = UNSET
    query_text: None | str | Unset = UNSET
    query_params: AssignmentPatchQueryParamsType0 | None | Unset = UNSET
    triggered_by: None | str | Unset = UNSET
    triggered_by_id: None | str | Unset = UNSET
    triggered_at: datetime.datetime | None | Unset = UNSET
    parent_assignment: None | str | Unset = UNSET
    artifacts_in: list[str] | None | Unset = UNSET
    artifacts_out: list[str] | None | Unset = UNSET
    sub_assignments: list[str] | None | Unset = UNSET
    monitor: AssignmentPatchMonitorType0 | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.assignment_patch_monitor_type_0 import AssignmentPatchMonitorType0
        from ..models.assignment_patch_query_params_type_0 import AssignmentPatchQueryParamsType0

        type_: None | str | Unset
        if isinstance(self.type_, Unset):
            type_ = UNSET
        else:
            type_ = self.type_

        status: None | str | Unset
        if isinstance(self.status, Unset):
            status = UNSET
        else:
            status = self.status

        query_text: None | str | Unset
        if isinstance(self.query_text, Unset):
            query_text = UNSET
        else:
            query_text = self.query_text

        query_params: dict[str, Any] | None | Unset
        if isinstance(self.query_params, Unset):
            query_params = UNSET
        elif isinstance(self.query_params, AssignmentPatchQueryParamsType0):
            query_params = self.query_params.to_dict()
        else:
            query_params = self.query_params

        triggered_by: None | str | Unset
        if isinstance(self.triggered_by, Unset):
            triggered_by = UNSET
        else:
            triggered_by = self.triggered_by

        triggered_by_id: None | str | Unset
        if isinstance(self.triggered_by_id, Unset):
            triggered_by_id = UNSET
        else:
            triggered_by_id = self.triggered_by_id

        triggered_at: None | str | Unset
        if isinstance(self.triggered_at, Unset):
            triggered_at = UNSET
        elif isinstance(self.triggered_at, datetime.datetime):
            triggered_at = self.triggered_at.isoformat()
        else:
            triggered_at = self.triggered_at

        parent_assignment: None | str | Unset
        if isinstance(self.parent_assignment, Unset):
            parent_assignment = UNSET
        else:
            parent_assignment = self.parent_assignment

        artifacts_in: list[str] | None | Unset
        if isinstance(self.artifacts_in, Unset):
            artifacts_in = UNSET
        elif isinstance(self.artifacts_in, list):
            artifacts_in = self.artifacts_in

        else:
            artifacts_in = self.artifacts_in

        artifacts_out: list[str] | None | Unset
        if isinstance(self.artifacts_out, Unset):
            artifacts_out = UNSET
        elif isinstance(self.artifacts_out, list):
            artifacts_out = self.artifacts_out

        else:
            artifacts_out = self.artifacts_out

        sub_assignments: list[str] | None | Unset
        if isinstance(self.sub_assignments, Unset):
            sub_assignments = UNSET
        elif isinstance(self.sub_assignments, list):
            sub_assignments = self.sub_assignments

        else:
            sub_assignments = self.sub_assignments

        monitor: dict[str, Any] | None | Unset
        if isinstance(self.monitor, Unset):
            monitor = UNSET
        elif isinstance(self.monitor, AssignmentPatchMonitorType0):
            monitor = self.monitor.to_dict()
        else:
            monitor = self.monitor

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if type_ is not UNSET:
            field_dict["type"] = type_
        if status is not UNSET:
            field_dict["status"] = status
        if query_text is not UNSET:
            field_dict["query_text"] = query_text
        if query_params is not UNSET:
            field_dict["query_params"] = query_params
        if triggered_by is not UNSET:
            field_dict["triggered_by"] = triggered_by
        if triggered_by_id is not UNSET:
            field_dict["triggered_by_id"] = triggered_by_id
        if triggered_at is not UNSET:
            field_dict["triggered_at"] = triggered_at
        if parent_assignment is not UNSET:
            field_dict["parent_assignment"] = parent_assignment
        if artifacts_in is not UNSET:
            field_dict["artifacts_in"] = artifacts_in
        if artifacts_out is not UNSET:
            field_dict["artifacts_out"] = artifacts_out
        if sub_assignments is not UNSET:
            field_dict["sub_assignments"] = sub_assignments
        if monitor is not UNSET:
            field_dict["monitor"] = monitor

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.assignment_patch_monitor_type_0 import AssignmentPatchMonitorType0
        from ..models.assignment_patch_query_params_type_0 import AssignmentPatchQueryParamsType0

        d = dict(src_dict)

        def _parse_type_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        type_ = _parse_type_(d.pop("type", UNSET))

        def _parse_status(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        status = _parse_status(d.pop("status", UNSET))

        def _parse_query_text(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        query_text = _parse_query_text(d.pop("query_text", UNSET))

        def _parse_query_params(data: object) -> AssignmentPatchQueryParamsType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                query_params_type_0 = AssignmentPatchQueryParamsType0.from_dict(data)

                return query_params_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(AssignmentPatchQueryParamsType0 | None | Unset, data)

        query_params = _parse_query_params(d.pop("query_params", UNSET))

        def _parse_triggered_by(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        triggered_by = _parse_triggered_by(d.pop("triggered_by", UNSET))

        def _parse_triggered_by_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        triggered_by_id = _parse_triggered_by_id(d.pop("triggered_by_id", UNSET))

        def _parse_triggered_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                triggered_at_type_0 = isoparse(data)

                return triggered_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        triggered_at = _parse_triggered_at(d.pop("triggered_at", UNSET))

        def _parse_parent_assignment(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        parent_assignment = _parse_parent_assignment(d.pop("parent_assignment", UNSET))

        def _parse_artifacts_in(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                artifacts_in_type_0 = cast(list[str], data)

                return artifacts_in_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        artifacts_in = _parse_artifacts_in(d.pop("artifacts_in", UNSET))

        def _parse_artifacts_out(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                artifacts_out_type_0 = cast(list[str], data)

                return artifacts_out_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        artifacts_out = _parse_artifacts_out(d.pop("artifacts_out", UNSET))

        def _parse_sub_assignments(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                sub_assignments_type_0 = cast(list[str], data)

                return sub_assignments_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        sub_assignments = _parse_sub_assignments(d.pop("sub_assignments", UNSET))

        def _parse_monitor(data: object) -> AssignmentPatchMonitorType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                monitor_type_0 = AssignmentPatchMonitorType0.from_dict(data)

                return monitor_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(AssignmentPatchMonitorType0 | None | Unset, data)

        monitor = _parse_monitor(d.pop("monitor", UNSET))

        assignment_patch = cls(
            type_=type_,
            status=status,
            query_text=query_text,
            query_params=query_params,
            triggered_by=triggered_by,
            triggered_by_id=triggered_by_id,
            triggered_at=triggered_at,
            parent_assignment=parent_assignment,
            artifacts_in=artifacts_in,
            artifacts_out=artifacts_out,
            sub_assignments=sub_assignments,
            monitor=monitor,
        )

        assignment_patch.additional_properties = d
        return assignment_patch

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
