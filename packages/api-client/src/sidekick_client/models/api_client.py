from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="ApiClient")


@_attrs_define
class ApiClient:
    """Machine API client credentials and authorization metadata.

    Attributes:
        id (str):
        name (str):
        key_prefix (str):
        key_hash (str):
        roles (list[str] | Unset):
        scopes (list[str] | Unset):
        status (str | Unset):  Default: 'active'.
        created_at (datetime.datetime | Unset):
        last_used_at (datetime.datetime | None | Unset):
        expires_at (datetime.datetime | None | Unset):
        rotated_from (None | str | Unset):
    """

    id: str
    name: str
    key_prefix: str
    key_hash: str
    roles: list[str] | Unset = UNSET
    scopes: list[str] | Unset = UNSET
    status: str | Unset = "active"
    created_at: datetime.datetime | Unset = UNSET
    last_used_at: datetime.datetime | None | Unset = UNSET
    expires_at: datetime.datetime | None | Unset = UNSET
    rotated_from: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        key_prefix = self.key_prefix

        key_hash = self.key_hash

        roles: list[str] | Unset = UNSET
        if not isinstance(self.roles, Unset):
            roles = self.roles

        scopes: list[str] | Unset = UNSET
        if not isinstance(self.scopes, Unset):
            scopes = self.scopes

        status = self.status

        created_at: str | Unset = UNSET
        if not isinstance(self.created_at, Unset):
            created_at = self.created_at.isoformat()

        last_used_at: None | str | Unset
        if isinstance(self.last_used_at, Unset):
            last_used_at = UNSET
        elif isinstance(self.last_used_at, datetime.datetime):
            last_used_at = self.last_used_at.isoformat()
        else:
            last_used_at = self.last_used_at

        expires_at: None | str | Unset
        if isinstance(self.expires_at, Unset):
            expires_at = UNSET
        elif isinstance(self.expires_at, datetime.datetime):
            expires_at = self.expires_at.isoformat()
        else:
            expires_at = self.expires_at

        rotated_from: None | str | Unset
        if isinstance(self.rotated_from, Unset):
            rotated_from = UNSET
        else:
            rotated_from = self.rotated_from

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "key_prefix": key_prefix,
                "key_hash": key_hash,
            }
        )
        if roles is not UNSET:
            field_dict["roles"] = roles
        if scopes is not UNSET:
            field_dict["scopes"] = scopes
        if status is not UNSET:
            field_dict["status"] = status
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if last_used_at is not UNSET:
            field_dict["last_used_at"] = last_used_at
        if expires_at is not UNSET:
            field_dict["expires_at"] = expires_at
        if rotated_from is not UNSET:
            field_dict["rotated_from"] = rotated_from

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        key_prefix = d.pop("key_prefix")

        key_hash = d.pop("key_hash")

        roles = cast(list[str], d.pop("roles", UNSET))

        scopes = cast(list[str], d.pop("scopes", UNSET))

        status = d.pop("status", UNSET)

        _created_at = d.pop("created_at", UNSET)
        created_at: datetime.datetime | Unset
        if isinstance(_created_at, Unset):
            created_at = UNSET
        else:
            created_at = isoparse(_created_at)

        def _parse_last_used_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                last_used_at_type_0 = isoparse(data)

                return last_used_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        last_used_at = _parse_last_used_at(d.pop("last_used_at", UNSET))

        def _parse_expires_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                expires_at_type_0 = isoparse(data)

                return expires_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        expires_at = _parse_expires_at(d.pop("expires_at", UNSET))

        def _parse_rotated_from(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        rotated_from = _parse_rotated_from(d.pop("rotated_from", UNSET))

        api_client = cls(
            id=id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            roles=roles,
            scopes=scopes,
            status=status,
            created_at=created_at,
            last_used_at=last_used_at,
            expires_at=expires_at,
            rotated_from=rotated_from,
        )

        api_client.additional_properties = d
        return api_client

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
