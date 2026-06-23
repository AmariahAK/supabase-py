import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from starlette.requests import Request
from starlette.datastructures import Headers


def _make_request(auth_header: str | None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"authorization", auth_header.encode())] if auth_header else [],
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_get_client_raises_401_when_no_auth_header():
    from dependencies import get_client
    request = _make_request(None)
    with pytest.raises(HTTPException) as exc_info:
        await get_client(request)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_client_raises_401_when_not_bearer():
    from dependencies import get_client
    request = _make_request("Basic dXNlcjpwYXNz")
    with pytest.raises(HTTPException) as exc_info:
        await get_client(request)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_client_returns_client_with_jwt():
    mock_client = AsyncMock()
    with patch("dependencies.acreate_client", AsyncMock(return_value=mock_client)):
        from dependencies import get_client
        request = _make_request("Bearer my-test-jwt")
        result = await get_client(request)
    assert result is mock_client
