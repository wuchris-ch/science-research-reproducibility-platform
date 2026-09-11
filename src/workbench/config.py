from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKBENCH_", env_file=".env", extra="ignore")
    data_dir: Path = ROOT / ".runtime"
    database_url: str = "sqlite:///" + str(ROOT / ".runtime/workbench.db")
    docker_context: str = "colima-research"
    image: str = "research-workbench-r:reference"
    origins: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000", "http://127.0.0.1:3000"]
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

    def initialize(self):
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.data_dir.chmod(0o700)
        for name in ("blobs", "datasets", "sources", "attempts", "exports"):
            (self.data_dir / name).mkdir(exist_ok=True, mode=0o700)
