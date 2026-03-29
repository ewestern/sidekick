from datetime import UTC, datetime, timedelta

from sqlmodel import Session, SQLModel, create_engine

from sidekick.api.auth import issue_api_key
from sidekick.core.models import ApiClient


def test_issue_api_key_persists_hashed_key() -> None:
    engine = create_engine("sqlite://")
    
    SQLModel.metadata.create_all(engine, tables=[ApiClient.__table__]) # type: ignore[attr-defined]

    with Session(engine) as session:
        issued = issue_api_key(
            session,
            name="worker-a",
            roles=["machine"],
            scopes=["sources:read"],
            created_by="admin",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        assert issued.plaintext_key.startswith("sk_")
        assert issued.client.key_hash
        assert issued.client.key_hash != issued.plaintext_key
        assert issued.client.roles == ["machine"]
        assert issued.client.scopes == ["sources:read"]
