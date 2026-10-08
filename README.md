# Bonayon backend (FastAPI)

Climate-smart crop planning and risk advisory for Bangladesh. FastAPI · SQLAlchemy 2.0 · PostgreSQL · Alembic · JWT · NASA POWER.

```
HTTP ─► API routes ─► deps (auth, roles) ─► services (engines) ─► repositories (queries, ownership) ─► models ─► PostgreSQL
                                                  └─► integrations (NASA POWER | mock climate provider)
```
Business logic never lives in route files. All engine weights/thresholds live in `app/core/agronomy.py`.

## Run it
**Windows (PowerShell or cmd), from the `backend` folder:**
```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
:: 1) create the database once (pgAdmin, or:  psql -U postgres -c "CREATE DATABASE bonayon;")
:: 2) create .env with a generated JWT_SECRET (put YOUR real PostgreSQL password in the URL):
python -m scripts.init_env "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/bonayon"
alembic upgrade head
python -m scripts.seed_all
python -m scripts.create_admin you@example.com "StrongPassword1" "Your Name"
uvicorn app.main:app --reload --port 8000
```
If you see *"Bonayon cannot start"* the message now says WHY: no `.env` at that path, a `.env.txt` that needs renaming, an empty file, or a file saved as UTF-16.
Repair any of these with `python -m scripts.init_env --force "<database url>"` (the old file is kept as `.env.bak`). The file must be named exactly `.env`. Special characters in the password (`@ : / # ? %`) are now encoded automatically, so a raw password such as `My@Pass1` works in `DATABASE_URL`.
If a connection fails, `alembic upgrade head` prints a short reason (server not running, wrong password, database missing) instead of a traceback.
Always use the virtual environment; the pinned versions in `requirements.txt` can clash with packages installed globally.

**macOS / Linux:**
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.init_env "postgresql+psycopg://user:password@localhost:5432/bonayon"   # creates .env with a random JWT_SECRET
alembic upgrade head                       # create tables
python -m scripts.seed_all                 # 64 districts + 8 crops (idempotent)
python -m scripts.create_admin you@example.com 'StrongPassword' 'Your Name'
uvicorn app.main:app --reload --port 8000  # docs: http://localhost:8000/docs
```
`CLIMATE_PROVIDER=mock` gives **synthetic** data (every climate response carries `source: "MOCK (synthetic development data)"`).
Use `nasa` for real data. The first request for a district downloads 20 years (several NASA calls, can take tens of seconds);
pre-warm with `python -m scripts.warm_climate Dhaka Rajshahi`.

## Tests
```bash
createdb bonayon_test        # any PostgreSQL database whose NAME contains "test"
export TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/bonayon_test   # PowerShell: $env:TEST_DATABASE_URL="..."   cmd: set TEST_DATABASE_URL=...
pytest
```
Tests use a real PostgreSQL (ARRAY/JSONB/enums), each test in a rolled-back transaction, and the mock climate provider.
**Last run in the build sandbox: 99 passed.** Not covered: the live NASA POWER service (no network there), load/performance, and email/phone edge cases.

## Environment variables
`DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM` (HS256), `ACCESS_TOKEN_EXPIRE_MINUTES` (1440), `CORS_ORIGINS` (comma-separated),
`CLIMATE_PROVIDER` (nasa|mock), `NASA_POWER_BASE_URL`, `TEST_DATABASE_URL`. No secrets are stored in code.

## Deploy: Neon + Render
Full walkthrough: **DEPLOYMENT.md** in this repository. Summary: Render build `bash build.sh` (installs, runs `alembic upgrade head`,
seeds districts/crops, optionally creates the first admin from `ADMIN_EMAIL`/`ADMIN_PASSWORD`), start
`uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'`,
env `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `CLIMATE_PROVIDER`, `PYTHON_VERSION=3.12.3`.

## Engines (all rule-based; no model training)
1. **Suitability**: `score = 100·(0.30·rain + 0.25·temp + 0.20·soil + 0.25·season) − risk_penalty`; ranges score 1.0 inside, decaying linearly to 0 outside; tiers ≥75 excellent / ≥55 good / ≥35 marginal.
2. **Risk calendar**: per month, average heatwave days (temp_max ≥ 35 °C), % of years with a 7+ day dry run (< 1 mm/day), first month averaging ≥ 50 mm = monsoon onset.
3. **Season plan**: best crop + a 2-month planting window with the lowest heatwave/dry-spell risk (Kharif starts no earlier than monsoon onset) + f-string advisory text.
4. **Rotation**: options from each crop's `rotation_after` list. 5. **Input estimator**: `area_decimal × seed_kg_per_decimal`, labeled an estimate.

## Deviations from the master prompt (deliberate, so you can defend or reverse them)
- **Sync SQLAlchemy and httpx** instead of async: simpler for a solo project; FastAPI runs `def` endpoints in a thread pool. No pytest-asyncio needed.
- **Risk penalty sign:** the prompt's `15×heatwave − 10×dryspell` makes dry-spell risk *raise* scores. Both are implemented as penalties (`+`). A test guards this.
- **Rainfall basis:** crop rain ranges are compared with the district's *annual* rainfall (matches the prompt's "1,850 mm vs 1,200–2,200 mm" example); temperature uses the *season's* average. Seasons are Rabi (Nov–Feb) and Kharif (Mar–Oct).
- **NASA timeout:** 10 s per request, but requests are split into 5-year chunks so a 20-year download does not hit one timeout.
- **Seeding by scripts** (idempotent) rather than an Alembic data migration.
- **LLM polish is not implemented** (advisory text is template-only).
- `climate_records` value columns are nullable, so a day NASA has no value for is still recorded and never re-requested.
- `plans_count` = number of saved season-plan recommendations. Engines return `503 INSUFFICIENT_DATA` when climate data is unavailable; read-only climate endpoints return `200` with `insufficient_data: true`.

## Limitations (honest)
- **NASA POWER client is unverified against the live service.** Its request/response shape (`properties.parameter.<PARAM>.<YYYYMMDD>`, fill value −999) is taken from NASA's documentation, validated strictly so a mismatch fails loudly, and tested with mocked HTTP only.
- **All crop ranges, weights, thresholds, seed rates and rotation lists are prototype assumptions**, not validated agronomy. District coordinates are approximate. Data is satellite-derived for the district HQ, not the farmer's field.
- Auth is a single JWT access token: no refresh, no server-side logout/revocation, no rate limiting or lockout. Passwords use bcrypt.
- Suitability and risk are computed from past averages; they do not forecast a specific season.
