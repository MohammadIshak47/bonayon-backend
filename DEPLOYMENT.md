# Backend deployment (GitHub → Neon → Render)

This repository is the **backend only**. The frontend is a separate repository (`bonayon-frontend`) deployed on Netlify.
Deploy the backend first, then the frontend, then come back to step 5 to set CORS.

## 1. Push to GitHub
Create an EMPTY repository named `bonayon-backend` (no README/.gitignore/license), then in this folder:
```
git init
git add .
git status        # must NOT list a file named .env, nor .venv
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/bonayon-backend.git
git push -u origin main
```

## 2. Neon database
1. neon.tech → Create project `bonayon`, region **AWS Asia Pacific (Singapore)**.
2. Click **Connect**, turn **Connection pooling OFF**, copy the string:
   `postgresql://user:password@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`
3. Do not create tables: the Render build does it.

## 3. Render web service
**Blueprint:** New → Blueprint → select this repo (reads `render.yaml`), fill the prompted variables, Apply.
**Manual:** New → Web Service → select this repo:

| Field | Value |
|---|---|
| Root Directory | (leave empty) |
| Runtime | Python 3 |
| Build Command | `bash build.sh` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'` |
| Health Check Path | `/health` |

| Env variable | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.3` |
| `DATABASE_URL` | Neon string |
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` (Blueprint generates it) |
| `CORS_ORIGINS` | `http://localhost:5173` for now; the Netlify URL in step 5 |
| `CLIMATE_PROVIDER` | `mock` first, `nasa` later |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME` | first admin, created during the build |

A good build log ends with: `Running upgrade -> 0001`, `seed: districts +64, crops +8`, `Created admin ...`, `Your service is live`.

Verify (first request may take 30–60 s, the free plan sleeps):
`https://<service>.onrender.com/health` → `{"status":"ok"}`, `/docs`, `/api/v1/districts`.
Write the Render URL down: the frontend needs it.

**Then delete `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME`** in Render → Environment (the admin already exists in the database).

## 4. Deploy the frontend
Follow `DEPLOYMENT.md` in the `bonayon-frontend` repository, using your Render URL as `VITE_API_URL`. Note the Netlify URL.

## 5. CORS
Render → Environment → set `CORS_ORIGINS` to the exact Netlify origin, e.g. `https://bonayon.netlify.app`
(scheme + host, no path; comma-separate several). Save; Render redeploys.

## Real NASA data
With `CLIMATE_PROVIDER=nasa` the first request per district downloads 20 years and can exceed the frontend's 15 s timeout.
Pre-warm from your PC: put the Neon `DATABASE_URL`, any `JWT_SECRET` and `CLIMATE_PROVIDER=nasa` in `.env`, then
```
py -3.12 -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
python -m scripts.warm_climate Dhaka Rajshahi Khulna
```
and set `CLIMATE_PROVIDER=nasa` on Render. The NASA client is only tested with mocked responses: check one district first.

## Moving existing local data to Neon (optional)
On an EMPTY Neon database, before the first Render deploy:
```
pg_dump --no-owner --no-acl "postgresql://postgres:PASSWORD@localhost:5432/bonayon" > bonayon.sql
psql "YOUR-NEON-STRING" -f bonayon.sql
```

## Updating
`git add . && git commit -m "change" && git push`: Render redeploys and runs new Alembic migrations automatically.

## Troubleshooting
| Problem | Fix |
|---|---|
| Browser: "blocked by CORS policy" | `CORS_ORIGINS` must equal the Netlify URL exactly. |
| Build fails at `alembic upgrade head` | Wrong/malformed `DATABASE_URL` (no spaces/quotes); the log shows the reason. Redeploy if Neon was waking. |
| "Bonayon cannot start: configuration is incomplete" | `DATABASE_URL` or `JWT_SECRET` missing. |
| passlib/`crypt` error | Python is not 3.12: set `PYTHON_VERSION=3.12.3`. |
| Cannot log in as admin | Re-add `ADMIN_EMAIL`/`ADMIN_PASSWORD`, Manual Deploy, delete them again. |
| First request very slow | Free Render/Neon waking up; open the site a few minutes before a demo. |
