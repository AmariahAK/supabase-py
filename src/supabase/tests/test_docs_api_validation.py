"""Verify that every API symbol documented in the task-oriented guide
exists in the actual supabase-py source at the pinned version (2.31.0).

This test serves as source-line validation for the documentation:
if a documented symbol is removed or renamed, this test will fail.
"""

import inspect

from supabase import (
    AsyncClient,
    AsyncClientOptions,
    Client,
    ClientOptions,
    __version__,
    acreate_client,
    create_async_client,
    create_client,
)
from supabase._async.client import SupabaseException as AsyncSupabaseException
from supabase._sync.client import SupabaseException as SyncSupabaseException


def test_version_is_2_31() -> None:
    assert __version__ == "2.31.0", f"Expected 2.31.0, got {__version__}"


# ── Factory Functions ─────────────────────────────────────────────


def test_create_client_exists() -> None:
    assert callable(create_client)


def test_create_async_client_exists() -> None:
    assert callable(create_async_client)


def test_acreate_client_exists() -> None:
    assert callable(acreate_client)


# ── Client Classes ────────────────────────────────────────────────


def test_sync_client_class() -> None:
    assert inspect.isclass(Client)


def test_async_client_class() -> None:
    assert inspect.isclass(AsyncClient)


# ── ClientOptions Classes ─────────────────────────────────────────


def test_client_options_class() -> None:
    assert inspect.isclass(ClientOptions)


def test_async_client_options_class() -> None:
    assert inspect.isclass(AsyncClientOptions)


# ── Sync Client API Surface ───────────────────────────────────────


def test_sync_client_table() -> None:
    assert hasattr(Client, "table")
    assert callable(Client.table)


def test_sync_client_from_() -> None:
    assert hasattr(Client, "from_")
    assert callable(Client.from_)


def test_sync_client_schema() -> None:
    assert hasattr(Client, "schema")
    assert callable(Client.schema)


def test_sync_client_rpc() -> None:
    assert hasattr(Client, "rpc")
    assert callable(Client.rpc)


def test_sync_client_postgrest() -> None:
    assert hasattr(Client, "postgrest")


def test_sync_client_storage() -> None:
    assert hasattr(Client, "storage")


def test_sync_client_functions() -> None:
    assert hasattr(Client, "functions")


def test_sync_client_channel() -> None:
    assert hasattr(Client, "channel")
    assert callable(Client.channel)


def test_sync_client_get_channels() -> None:
    assert hasattr(Client, "get_channels")
    assert callable(Client.get_channels)


def test_sync_client_remove_channel() -> None:
    assert hasattr(Client, "remove_channel")
    assert callable(Client.remove_channel)


def test_sync_client_remove_all_channels() -> None:
    assert hasattr(Client, "remove_all_channels")
    assert callable(Client.remove_all_channels)


# ── Async Client API Surface ──────────────────────────────────────


def test_async_client_table() -> None:
    assert hasattr(AsyncClient, "table")
    assert callable(AsyncClient.table)


def test_async_client_rpc() -> None:
    assert hasattr(AsyncClient, "rpc")
    assert callable(AsyncClient.rpc)


def test_async_client_postgrest() -> None:
    assert hasattr(AsyncClient, "postgrest")


def test_async_client_storage() -> None:
    assert hasattr(AsyncClient, "storage")


def test_async_client_functions() -> None:
    assert hasattr(AsyncClient, "functions")


def test_async_client_channel() -> None:
    assert hasattr(AsyncClient, "channel")
    assert callable(AsyncClient.channel)


# ── ClientOptions Fields ──────────────────────────────────────────


def test_client_options_fields() -> None:
    fields = {f.name for f in ClientOptions.__dataclass_fields__.values()}
    expected = {
        "schema",
        "headers",
        "auto_refresh_token",
        "persist_session",
        "realtime",
        "postgrest_client_timeout",
        "storage_client_timeout",
        "function_client_timeout",
        "flow_type",
    }
    assert expected.issubset(fields), f"Missing fields: {expected - fields}"


def test_sync_client_options_extra_fields() -> None:
    """SyncClientOptions adds storage and httpx_client."""
    from supabase.lib.client_options import SyncClientOptions

    fields = {f.name for f in SyncClientOptions.__dataclass_fields__.values()}
    assert "storage" in fields
    assert "httpx_client" in fields


def test_async_client_options_extra_fields() -> None:
    """AsyncClientOptions adds storage and httpx_client."""
    fields = {f.name for f in AsyncClientOptions.__dataclass_fields__.values()}
    assert "storage" in fields
    assert "httpx_client" in fields


# ── Auth Client Surface (on client.auth) ──────────────────────────


def test_auth_methods_exist() -> None:
    """Verify key auth methods exist on the auth client type."""
    from supabase._sync.auth_client import SyncSupabaseAuthClient

    methods = [
        "sign_up",
        "sign_in_with_password",
        "sign_in_with_oauth",
        "sign_in_with_otp",
        "sign_in_with_sso",
        "sign_in_anonymously",
        "exchange_code_for_session",
        "sign_out",
        "get_session",
        "refresh_session",
        "get_user",
        "update_user",
        "on_auth_state_change",
    ]
    for method in methods:
        assert hasattr(SyncSupabaseAuthClient, method), (
            f"Auth client missing method: {method}"
        )
        assert callable(getattr(SyncSupabaseAuthClient, method))


# ── Error Classes ─────────────────────────────────────────────────


def test_supabase_exception() -> None:
    assert inspect.isclass(SyncSupabaseException)
    assert inspect.isclass(AsyncSupabaseException)


def test_functions_errors() -> None:
    from supabase import FunctionsHttpError, FunctionsRelayError

    assert inspect.isclass(FunctionsHttpError)
    assert inspect.isclass(FunctionsRelayError)


def test_auth_errors() -> None:
    from supabase import (
        AuthApiError,
        AuthInvalidCredentialsError,
        AuthSessionMissingError,
        AuthWeakPasswordError,
    )

    assert inspect.isclass(AuthApiError)
    assert inspect.isclass(AuthInvalidCredentialsError)
    assert inspect.isclass(AuthSessionMissingError)
    assert inspect.isclass(AuthWeakPasswordError)
