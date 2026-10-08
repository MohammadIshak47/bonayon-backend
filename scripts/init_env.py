"""Create backend/.env from .env.example with a freshly generated JWT_SECRET.

Usage (run from the backend folder, works on Windows, macOS and Linux):
    python -m scripts.init_env "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/bonayon"
    python -m scripts.init_env --force "<url>"     # replace an existing/broken .env (the old one is kept as .env.bak)

Passwords with special characters (@ : / # %) must be URL-encoded inside the URL, e.g. @ -> %40.
This script deliberately imports nothing from the app, so it works before the app is configured.
"""
import secrets
import sys
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/bonayon"


def encode_password(url: str) -> str:
    """Percent-encode the password (e.g. My@Pass1 -> My%40Pass1). Same rule as app/core/config.py."""
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    at = rest.split("?", 1)[0].rfind("@")
    if at == -1:
        return url
    user, colon, password = rest[:at].partition(":")
    return url if not colon else f"{scheme}://{user}:{quote(unquote(password), safe='')}@{rest[at + 1:]}"


def main() -> None:
    target = ROOT / ".env"
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv[1:]
    if target.exists() and not force:
        print(f"{target} already exists; not overwriting it. To replace a broken one, add --force (the old file is saved as .env.bak).")
        return
    if target.exists():
        target.replace(ROOT / ".env.bak")
        print("Old .env saved as .env.bak")
    db_url = encode_password(args[0]) if args else DEFAULT_URL
    out = []
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            line = f"DATABASE_URL={db_url}"
        elif line.startswith("JWT_SECRET="):
            line = f"JWT_SECRET={secrets.token_urlsafe(48)}"
        out.append(line)
    target.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Created {target}")
    if "YOUR_PASSWORD" in db_url:
        print("NEXT: open .env and replace YOUR_PASSWORD (and the database name if different) with your PostgreSQL details.")


if __name__ == "__main__":
    main()
