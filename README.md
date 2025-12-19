# BookMyShow Backend (FastAPI + Supabase-ready)

Python backend for BookMyShow-style app with in-memory seat locking and seed data. Uses FastAPI; ready to plug Supabase Postgres/Auth when credentials are provided.

## Prereqs
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) installed (`pip install uv` if missing)
- Supabase project (free tier) if you want persistence

## Setup
```powershell
cd backend
uv venv .venv
uv pip install -e .
# or uv sync
cp .env.example .env
```
Fill `.env` with your Supabase keys.

## Run dev server
```powershell
uv run uvicorn app.main:app --reload --port 8000
```
API will be at http://localhost:8000

## Key endpoints
- GET `/health`
- GET `/cities`
- GET `/movies?q=`
- GET `/venues?cityId=`
- GET `/shows?movieId=&venueId=`
- GET `/shows/{showId}/seats`
- POST `/shows/{showId}/lock` `{ "seats": ["gold-A1"] }`
- POST `/bookings` `{ "show_id": "s_1", "seats": ["gold-A1"], "lock_id": "..." }`
- POST `/payments/mock` `{ "booking_id": "...", "outcome": "success"|"fail" }`
- GET `/bookings/history`

## Notes
- Seat locking is in-memory (per process). For multi-instance deployments, swap `InMemoryLockManager` with Redis/Postgres-based locks.
- Catalog and seats are seeded in-memory for demo; replace with Supabase repositories for production.
- Payment is mocked; no real gateway needed.

## Recommended next steps
1. Connect Supabase: create tables per design (cities, movies, venues, screens, shows, seats, bookings, payments) and wire repositories.
2. Add auth via Supabase JWT and protect booking/history routes.
3. Deploy on Render/Fly/railway or containerize; set env vars.
