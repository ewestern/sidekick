from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.api_client_rotate import ApiClientRotate
from ...models.api_key_issued_response import ApiKeyIssuedResponse
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    client_id: str,
    *,
    body: ApiClientRotate,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api-clients/{client_id}/rotate".format(
            client_id=quote(str(client_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ApiKeyIssuedResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ApiKeyIssuedResponse.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ApiKeyIssuedResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    client_id: str,
    *,
    client: AuthenticatedClient,
    body: ApiClientRotate,
) -> Response[ApiKeyIssuedResponse | HTTPValidationError]:
    """Rotate Api Client Key

    Args:
        client_id (str):
        body (ApiClientRotate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiKeyIssuedResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        client_id=client_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    client_id: str,
    *,
    client: AuthenticatedClient,
    body: ApiClientRotate,
) -> ApiKeyIssuedResponse | HTTPValidationError | None:
    """Rotate Api Client Key

    Args:
        client_id (str):
        body (ApiClientRotate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiKeyIssuedResponse | HTTPValidationError
    """

    return sync_detailed(
        client_id=client_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    client_id: str,
    *,
    client: AuthenticatedClient,
    body: ApiClientRotate,
) -> Response[ApiKeyIssuedResponse | HTTPValidationError]:
    """Rotate Api Client Key

    Args:
        client_id (str):
        body (ApiClientRotate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ApiKeyIssuedResponse | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        client_id=client_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    client_id: str,
    *,
    client: AuthenticatedClient,
    body: ApiClientRotate,
) -> ApiKeyIssuedResponse | HTTPValidationError | None:
    """Rotate Api Client Key

    Args:
        client_id (str):
        body (ApiClientRotate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ApiKeyIssuedResponse | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client_id=client_id,
            client=client,
            body=body,
        )
    ).parsed
