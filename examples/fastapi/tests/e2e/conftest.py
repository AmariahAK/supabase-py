"""
E2E test fixtures.

Requires a running local Supabase instance and the following env vars:
  SUPABASE_URL        — from `supabase status -o env` → API_URL
  SUPABASE_SERVICE_KEY — SERVICE_ROLE_KEY
  SUPABASE_ANON_KEY    — ANON_KEY

Start infrastructure: make start-infra (from examples/fastapi/)
"""

import os
import random
import string
import subprocess
import time
from pathlib import Path

import httpx
import pytest
from supabase import acreate_client
from supabase.lib.client_options import AsyncClientOptions

SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54341")
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]

FASTAPI_DIR = Path(__file__).parent.parent.parent
APP_PORT = 8877
APP_BASE_URL = f"http://127.0.0.1:{APP_PORT}"


def _random_suffix(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=n))


@pytest.fixture(scope="session")
def running_app():
    """Start the FastAPI app (including engine) as a uvicorn subprocess."""
    env = {
        **os.environ,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_SERVICE_KEY": SUPABASE_SERVICE_KEY,
        "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
    }
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(APP_PORT),
            "--log-level",
            "warning",
        ],
        cwd=FASTAPI_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    deadline = time.time() + 45
    started = False
    while time.time() < deadline:
        try:
            r = httpx.get(f"{APP_BASE_URL}/", timeout=2)
            if r.status_code < 500:
                started = True
                break
        except Exception:
            pass
        time.sleep(0.4)

    if not started:
        stderr_out = ""
        if proc.stderr:
            proc.stderr.read(8192)
        proc.terminate()
        pytest.fail(
            f"FastAPI app did not start within 45s on port {APP_PORT}. stderr:\n{stderr_out}"
        )

    yield APP_BASE_URL

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
async def service_client():
    """Service-role AsyncClient — bypasses RLS. Created fresh per test."""
    client = await acreate_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    yield client
    await client.realtime.close()


@pytest.fixture
async def user_a(service_client):
    """Create a real Supabase user and return credentials. Cleaned up after the test."""
    email = f"e2e_a_{_random_suffix()}@example.com"
    password = "Password123!"
    resp = await service_client.auth.sign_up({"email": email, "password": password})
    assert resp.session, f"sign_up returned no session for {email}"
    token = resp.session.access_token
    user_id = resp.user.id

    options = AsyncClientOptions()
    options.headers["Authorization"] = f"Bearer {token}"
    anon_client = await acreate_client(SUPABASE_URL, SUPABASE_ANON_KEY, options=options)

    yield {"token": token, "user_id": user_id, "email": email, "client": anon_client}

    await service_client.auth.admin.delete_user(user_id)


@pytest.fixture
async def user_b(service_client):
    """A second user for RLS isolation tests. Cleaned up after the test."""
    email = f"e2e_b_{_random_suffix()}@example.com"
    password = "Password123!"
    resp = await service_client.auth.sign_up({"email": email, "password": password})
    assert resp.session, f"sign_up returned no session for {email}"
    token = resp.session.access_token
    user_id = resp.user.id

    options = AsyncClientOptions()
    options.headers["Authorization"] = f"Bearer {token}"
    anon_client = await acreate_client(SUPABASE_URL, SUPABASE_ANON_KEY, options=options)

    yield {"token": token, "user_id": user_id, "email": email, "client": anon_client}

    await service_client.auth.admin.delete_user(user_id)


@pytest.fixture
async def client_a(running_app, user_a):
    """httpx.AsyncClient pre-configured with user A's auth token."""
    async with httpx.AsyncClient(
        base_url=running_app,
        headers={"Authorization": f"Bearer {user_a['token']}"},
        timeout=10,
    ) as client:
        yield client


@pytest.fixture
async def client_b(running_app, user_b):
    """httpx.AsyncClient pre-configured with user B's auth token."""
    async with httpx.AsyncClient(
        base_url=running_app,
        headers={"Authorization": f"Bearer {user_b['token']}"},
        timeout=10,
    ) as client:
        yield client
