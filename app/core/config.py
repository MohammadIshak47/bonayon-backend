"""Settings loaded from environment / .env. No secrets live in code."""
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, unquote
from typing import Literal

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Use the psycopg v3 driver and percent-encode the password, so a raw password containing @ : / # ? %
    (e.g. 'My@Pass1') works when pasted into DATABASE_URL. Already-encoded passwords are left unchanged."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix):]
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    before_query = rest.split("?", 1)[0]
    at = before_query.rfind("@")  # the LAST @ separates credentials from the host
    if at == -1:
        return url
    user, colon, password = rest[:at].partition(":")
    if not colon:
        return url
    return f"{scheme}://{user}:{quote(unquote(password), safe='')}@{rest[at + 1:]}"


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # Absolute path (the backend folder), so it works no matter which folder the command is run from.
    # utf-8-sig also accepts files saved by Notepad "with BOM".
    model_config = SettingsConfigDict(env_file=str(ENV_PATH), env_file_encoding="utf-8-sig", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = "http://localhost:5173"  # comma-separated allowlist
    CLIMATE_PROVIDER: Literal["nasa", "mock"] = "mock"
    NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal/daily/point"
    NASA_TIMEOUT_S: float = 10.0
    NASA_RETRIES: int = 2
    CLIMATE_END_LAG_DAYS: int = 7  # NASA POWER daily data lags real time by a few days

    @field_validator("DATABASE_URL")
    @classmethod
    def _driver(cls, v: str) -> str:
        # Neon/Render give postgres:// or postgresql://; we use the psycopg (v3) driver.
        return normalize_database_url(v)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]  # browsers send origins without a trailing /


def _env_diagnosis(env_path: Path) -> list[str]:
    """Explain WHY the .env file is not usable (names only, never values)."""
    out = [f"  Expected file: {env_path}"]
    if env_path.exists():
        raw = env_path.read_bytes()
        out.append(f"  The file exists ({len(raw)} bytes).")
        if not raw.strip():
            out.append('  -> It is EMPTY. Recreate it:  python -m scripts.init_env --force "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/bonayon"')
        elif raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
            out.append('  -> It was saved as UTF-16 (Notepad "Unicode"). Re-save as UTF-8, or recreate it with: python -m scripts.init_env --force "<url>"')
        else:
            names = [ln.split("=", 1)[0].strip() for ln in raw.decode("utf-8-sig", "replace").splitlines() if "=" in ln and not ln.lstrip().startswith("#")]
            out.append(f"  -> Variable names found inside: {', '.join(names) or '(none)'}")
    else:
        out.append("  The file does NOT exist at that path.")
        for name in (".env.txt", "env", "env.txt", ".env.example.txt"):
            if (env_path.parent / name).exists():
                out.append(f"  -> Found '{name}' in that folder. Rename it to exactly .env (in File Explorer: View > Show > File name extensions).")
    return out


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except UnicodeDecodeError:
        raise RuntimeError("\n".join([
            "", "Bonayon cannot start: the .env file cannot be read as UTF-8 text.", *_env_diagnosis(ENV_PATH),
            '  Fix: recreate it with:  python -m scripts.init_env --force "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/bonayon"',
        ])) from None
    except ValidationError as exc:
        missing = [str(e["loc"][0]) for e in exc.errors() if e["type"] == "missing"]
        invalid = [f"{e['loc'][0]}: {e['msg']}" for e in exc.errors() if e["type"] != "missing"]
        lines = ["", "Bonayon cannot start: configuration is incomplete."]
        if missing:
            lines.append(f"  Missing: {', '.join(missing)}")
        lines += [f"  Invalid: {i}" for i in invalid]
        lines += [
            *_env_diagnosis(ENV_PATH),
            "  Fix: the backend folder needs a file named exactly .env (not .env.txt) containing DATABASE_URL and JWT_SECRET.",
            "  Easiest: python -m scripts.init_env \"postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/bonayon\"",
            "  (Details: see .env.example and README.md)",
        ]
        raise RuntimeError("\n".join(lines)) from None
