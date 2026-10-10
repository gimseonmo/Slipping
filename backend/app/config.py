from __future__ import annotations

import secrets
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Slipping"
    host: str = "0.0.0.0"
    port: int = 8787
    root_dir: Path = Path(__file__).resolve().parents[2]
    frontend_dist: Path = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    max_upload_bytes: int = 100 * 1024 * 1024
    session_token: str = secrets.token_urlsafe(18)

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def state_dir(self) -> Path:
        return self.data_dir / "state"


settings = Settings()
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
settings.state_dir.mkdir(parents=True, exist_ok=True)
