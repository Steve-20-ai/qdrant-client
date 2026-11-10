import httpx
import pytest

from qdrant_client import AsyncQdrantClient, QdrantClient

CLIENTS = [QdrantClient, AsyncQdrantClient]


def make_client(client_type, **kwargs):
    # check_compatibility=False keeps the client from talking to a server, so the
    # metadata it would send can be inspected offline.
    return client_type(
        host="localhost", prefer_grpc=True, check_compatibility=False, **kwargs
    )


def rest_api_key_values(client) -> list:
    """The `api-key` values httpx would put on the wire, in order."""
    request = httpx.Request(
        "GET", "https://localhost:6333/collections", headers=client._client._rest_headers
    )
    return request.headers.get_list("api-key")


@pytest.mark.parametrize("client_type", CLIENTS)
def test_api_key_replaces_header_in_grpc_metadata(client_type) -> None:
    client = make_client(
        client_type,
        https=True,
        api_key="from-param",
        headers={"api-key": "from-headers", "x-custom": "kept"},
    )

    assert client._client._grpc_headers == [
        ("x-custom", "kept"),
        ("api-key", "from-param"),
    ]
    assert client._client._rest_headers["api-key"] == "from-param"


@pytest.mark.parametrize("client_type", CLIENTS)
def test_api_key_replaces_header_with_any_casing(client_type) -> None:
    client = make_client(
        client_type,
        https=True,
        api_key="from-param",
        headers={"Api-Key": "from-headers"},
    )

    assert client._client._grpc_headers == [("api-key", "from-param")]


@pytest.mark.parametrize("client_type", CLIENTS)
def test_api_key_replaces_rest_header_with_any_casing(client_type) -> None:
    # a dict keeps "Api-Key" and "api-key" as separate entries, so assigning the
    # parameter alone would leave both on the request, old value first.
    client = make_client(
        client_type,
        https=True,
        api_key="from-param",
        headers={"Api-Key": "from-headers", "x-custom": "kept"},
    )

    assert rest_api_key_values(client) == ["from-param"]
    assert client._client._rest_headers["x-custom"] == "kept"


@pytest.mark.parametrize("client_type", CLIENTS)
def test_api_key_replaces_rest_header_when_spelling_matches(client_type) -> None:
    client = make_client(
        client_type,
        https=True,
        api_key="from-param",
        headers={"api-key": "from-headers"},
    )

    assert rest_api_key_values(client) == ["from-param"]


@pytest.mark.parametrize("client_type", CLIENTS)
def test_api_key_replaces_api_key_from_metadata(client_type) -> None:
    # `metadata` lands in the REST headers only, so it needs the same treatment.
    client = make_client(
        client_type,
        https=True,
        api_key="from-param",
        metadata={"api-key": "from-metadata", "x-custom": "kept"},
    )

    assert rest_api_key_values(client) == ["from-param"]
    assert client._client._rest_headers["x-custom"] == "kept"


@pytest.mark.parametrize("client_type", CLIENTS)
def test_api_key_is_sent_once_without_headers(client_type) -> None:
    client = make_client(client_type, https=True, api_key="from-param")

    assert client._client._grpc_headers == [("api-key", "from-param")]
    assert rest_api_key_values(client) == ["from-param"]


@pytest.mark.parametrize("client_type", CLIENTS)
def test_header_is_kept_when_no_api_key_is_given(client_type) -> None:
    client = make_client(client_type, https=True, headers={"api-key": "from-headers"})

    assert client._client._grpc_headers == [("api-key", "from-headers")]
    assert rest_api_key_values(client) == ["from-headers"]


@pytest.mark.parametrize("client_type", CLIENTS)
def test_header_is_kept_when_api_key_is_none(client_type) -> None:
    # `api_key=None` is the documented way to say "authenticate with headers only"
    client = make_client(
        client_type,
        https=True,
        api_key=None,
        headers={"Api-Key": "from-headers"},
    )

    assert rest_api_key_values(client) == ["from-headers"]
