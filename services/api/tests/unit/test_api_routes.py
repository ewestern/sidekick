from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlmodel import Session

from sidekick.api.auth import AuthContext, CallerType, get_auth_context
from sidekick.api.db import get_session
from sidekick.api.main import create_app
from sidekick.core.models import AgentConfig, ApiClient, Assignment, Source


class _Result:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values

    def first(self) -> object | None:
        return self._values[0] if self._values else None


class _FakeSession:
    def __init__(self) -> None:
        self.sources: dict[str, Source] = {}
        self.assignments: dict[str, Assignment] = {}
        self.agent_configs: dict[str, AgentConfig] = {}
        self.api_clients: dict[str, ApiClient] = {}

    def get(self, model: type, row_id: str):
        if model is Source:
            return self.sources.get(row_id)
        if model is Assignment:
            return self.assignments.get(row_id)
        if model is ApiClient:
            return self.api_clients.get(row_id)
        return None

    def exec(self, _stmt):
        # Current tests only need "no existing agent config by agent_id".
        return _Result([])

    def add(self, row: object) -> None:
        if isinstance(row, Source):
            self.sources[row.id] = row
        elif isinstance(row, Assignment):
            self.assignments[row.id] = row
        elif isinstance(row, AgentConfig):
            self.agent_configs[row.agent_id] = row
        elif isinstance(row, ApiClient):
            self.api_clients[row.id] = row

    def commit(self) -> None:
        return None

    def refresh(self, _row: object) -> None:
        return None

    def delete(self, row: object) -> None:
        if isinstance(row, Source):
            self.sources.pop(row.id, None)


def _make_client(roles: set[str]) -> TestClient:
    app = create_app()
    fake_session = _FakeSession()

    def _session_override() -> Generator[Session, None, None]:
        yield fake_session  # type: ignore[misc]

    def _auth_override() -> AuthContext:
        return AuthContext(
            subject="test-user",
            caller_type=CallerType.USER,
            roles=roles,
            scopes=set(),
        )

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_auth_context] = _auth_override
    return TestClient(app)


def test_sources_crud_for_editor_role() -> None:
    client = _make_client({"editor"})
    create_resp = client.post(
        "/sources", json={"id": "src-1", "name": "City Council Feed"})
    assert create_resp.status_code == 200
    assert create_resp.json()["status"] == "active"

    get_resp = client.get("/sources/src-1")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "City Council Feed"

    patch_resp = client.patch("/sources/src-1", json={"name": "Updated Name"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Updated Name"

    delete_resp = client.delete("/sources/src-1")
    assert delete_resp.status_code == 204


def test_admin_can_manage_agent_configs() -> None:
    client = _make_client({"admin"})
    create_resp = client.post(
        "/agent-configs",
        json={
            "id": "cfg_1",
            "agent_id": "editor-agent",
            "model": "gpt-4o-mini",
            "prompts": {"system": "You are helpful"},
            "skills": ["news-values"],
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["agent_id"] == "editor-agent"

    put_resp = client.put(
        "/agent-configs/editor-agent",
        json={
            "model": "gpt-4.1-mini",
            "prompts": {"system": "Updated"},
            "skills": [],
        },
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["model"] == "gpt-4.1-mini"


def test_non_admin_blocked_from_agent_config_writes() -> None:
    client = _make_client({"editor"})
    resp = client.post(
        "/agent-configs",
        json={
            "id": "cfg_2",
            "agent_id": "beat-agent",
            "model": "gpt-4.1-mini",
            "prompts": {"system": "Nope"},
            "skills": [],
        },
    )
    assert resp.status_code == 403


def test_artifact_create_is_omitted() -> None:
    client = _make_client({"admin"})
    resp = client.post("/artifacts", json={"id": "art_1"})
    assert resp.status_code == 405
