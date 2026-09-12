from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKBENCH_", env_file=".env", extra="ignore")
    data_dir: Path = ROOT / ".runtime"
    database_url: str = ""
    docker_context: str = "colima-research"
    image: str = "research-workbench-r:reference"
    origins: list[str] = ["http://localhost:8317", "http://127.0.0.1:8317", "http://localhost:3000", "http://127.0.0.1:3000"]
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    model_url: str = ""
    model_key: str = ""
    model_name: str = ""
    model_input_per_million: float = 0
    model_output_per_million: float = 0
    model_budget_usd: float = 2
    lease_seconds: int = 30
    max_attempts: int = 3

    @model_validator(mode="after")
    def database_default(self):
        if not self.database_url:
            self.database_url = "sqlite:///" + str(self.data_dir / "workbench.db")
        return self

    def initialize(self):
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.data_dir.chmod(0o700)
        for name in ("blobs", "datasets", "sources", "attempts", "exports"):
            (self.data_dir / name).mkdir(exist_ok=True, mode=0o700)
