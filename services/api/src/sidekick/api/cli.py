"""CLI for running the API service."""

import typer
import uvicorn
from dotenv import load_dotenv

app = typer.Typer(help="Run the Sidekick API server.")


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8080, reload: bool = False) -> None:
    """Start uvicorn with the API app."""
    # Local convenience: load .env when present without overriding shell env.
    load_dotenv(override=False)
    uvicorn.run("sidekick.api.main:app", host=host, port=port, reload=reload)


def main() -> None:
    """CLI entrypoint."""
    app()
