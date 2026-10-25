# Campus Pulse — AI-Powered College Club & Event Coordination System

One home for every club, every stage, every event. Clubs post events, students register, and four AI components keep the week conflict-free.

**Stack:** React 18 + Vite + plain CSS · Python Flask + SQLAlchemy · MySQL (MariaDB works too) · JWT auth

The UI recreates the three PPT mockups: **Home**, **Weekly event feed**, **Event detail & AI insights** (deep forest green, ivory ticket cards, mustard accents, serif headlines).

## Deploy (recommended: ONE service, no CORS, no API-URL setup)

The Docker image builds the React app and Flask serves it together with the API, so the site and `/api` live at the same URL.
This avoids the classic "Request failed (404)" you get when the frontend is on Vercel without a backend URL.

**Railway (about 10 minutes)**
1. Push this folder to GitHub (the folder containing `Dockerfile` must be the repo root, or set Railway's *Root Directory* to it).
2. Railway → New Project → *Deploy from GitHub repo*. It detects the `Dockerfile`.
3. In the same project click *New → Database → MySQL*.
4. On the web service → *Variables*, add:
   - `DATABASE_URL` = reference the MySQL service's `MYSQL_URL` (the `mysql://` form is converted automatically)
   - `SECRET_KEY` = a long random string
   - `AUTO_SEED` = `1` (loads the fictional demo data on the first start)
5. Web service → *Settings → Networking → Generate Domain*. Open the domain: the app is live.
6. Check `https://YOUR-DOMAIN/api/health` returns `{"status":"ok"}`.

After the first start, remove `AUTO_SEED` (or leave it, it only seeds an empty database). Change the demo passwords before sharing the link.
Other Docker hosts work the same way: set `DATABASE_URL`, `SECRET_KEY`, optionally `AUTO_SEED=1`, and expose `$PORT`.

**Frontend on Vercel + backend elsewhere (only if you want two services)**
Set Vercel *Root Directory* to `frontend`, add `VITE_API_URL=https://YOUR-BACKEND/api` (then **redeploy**, Vite bakes it in at build time), and set the backend's `CORS_ORIGINS` to your Vercel URL. `frontend/vercel.json` already contains the router rewrite.

**Without Docker:** `cd frontend && npm install && npm run build`, then `cd backend && gunicorn run:app` - Flask serves `frontend/dist` automatically.

## Folder layout
```
campus-pulse/
├── backend/            Flask API
│   ├── app/ai/         ← the 4 AI algorithms (pure Python, easy to read & test)
│   ├── app/routes/     API endpoints (auth, events, clubs, venues, me, admin, reports, ai)
│   ├── app/services/   insights.py: loads DB data and feeds the AI modules
│   ├── tests/          pytest suite (AI unit tests + API tests)
│   ├── seed.py         demo data generator
│   └── requirements.txt, .env.example, run.py, config.py
├── database/           schema.sql, seed.sql
├── frontend/           React app (src/pages, src/components, src/api, src/styles)
├── Dockerfile, render.yaml, .dockerignore   one-service deployment
└── README.md
```

## Quick start

### 1. Requirements
Python 3.10+, Node 18+, MySQL 8 (or MariaDB 10.5+).

### 2. Database
```bash
mysql -u root -p -e "CREATE DATABASE campus_pulse CHARACTER SET utf8mb4;
  CREATE USER 'campus_user'@'localhost' IDENTIFIED BY 'campus_password';
  GRANT ALL ON campus_pulse.* TO 'campus_user'@'localhost'; FLUSH PRIVILEGES;"
```
Change the user/password if you like and keep them in `backend/.env` (next step). No MySQL? Set `DATABASE_URL=sqlite:///campus.db` in `.env` as a local fallback.

### 3. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # edit DB_* values and SECRET_KEY
python seed.py --reset                                # creates tables + fictional demo data
python run.py                                         # API on http://localhost:5000
```
Prefer SQL files? `mysql -u root -p < database/schema.sql` then `mysql -u root -p campus_pulse < database/seed.sql` does the same (seed.sql has fixed dates; `seed.py` always generates dates relative to today, which is better for demos).

### 4. Frontend
```bash
cd frontend
npm install
npm run dev                                           # http://localhost:5173 (proxies /api to Flask)
```
Production build: `npm run build` (output in `frontend/dist`). If you host the API elsewhere set `VITE_API_URL`.

### 5. Demo accounts (fictional)
| Role | Email | Password |
|---|---|---|
| Admin | admin@campus.test | Admin@123 |
| Coordinator (Tech, Robotics, E-Cell) | priya@campus.test | Coord@123 |
| Coordinator (Music, Drama, Photography) | rahul@campus.test | Coord@123 |
| Coordinator (Sports, Literary) | meera@campus.test | Coord@123 |
| Student | student@campus.test | Student@123 |

The demo student is registered for two overlapping events so the clash alerts are visible straight away.

## Features → where to find them
| Feature | Page |
|---|---|
| Home, featured events, live club stats | `/` |
| Weekly feed: category filters, search, week switch, conflict stamps | `/events` |
| Event details, register/cancel, attendance metrics, AI insights | `/events/:id` |
| Login / register / logout, role-based access | `/login`, `/register` |
| Clubs: browse, join/leave, create, manage members, publish activities | `/clubs`, `/coordinator` → *Clubs & members* |
| Events: create, edit, publish, cancel, delete (live conflict check in form) | `/coordinator`, `/coordinator/events/new` |
| Venues: capacity, facilities, hours, availability by date, blackouts, add/edit/delete | `/venues`, `/admin` → *Venues* |
| Student dashboard + calendar + notifications | `/dashboard`, `/calendar` |
| Coordinator dashboard + AI recommendations | `/coordinator` |
| Admin dashboard: users/roles, clubs, venues, events, AI conflicts | `/admin` |
| Attendance recording + attendance rate | `/coordinator/events/:id/attendance` |
| Reports: participation, club activity, venue utilization, CSV export | `/reports` |

Roles: **student** (browse, register, join clubs) · **coordinator** (everything for clubs they coordinate) · **admin** (everything + users and venues). Self-registration always creates a student; an admin promotes users.

## The four AI components (`backend/app/ai/`)
All are deterministic, explainable algorithms; the UI shows their real output.

1. **Conflict Detector** (`conflict_detector.py`) — flags venue double-booking, venue blackouts, outside-opening-hours, capacity overflow (all via time-range overlap) and campus-wide time overlaps. High-severity conflicts block publishing.
2. **Student Overlap Analyzer** (`overlap_analyzer.py`) — intersects registration sets of events that run at the same time and counts *unique* affected students (names are shown to organizers only).
3. **Attendance Predictor** (`attendance_predictor.py`) — smoothed historical show-rate from past events with recorded attendance (club → category → campus scope, minimum 3 events), minus 0.5 attendee per student torn between clashing events. With fewer than 3 usable past events it **falls back to a default 65% show-rate and says so** (`method: fallback_default`). It also outputs *venue fit* and *conflict-free* scores shown as the confidence bars.
4. **Schedule Optimizer** (`schedule_optimizer.py`) — evaluates every half-hour start within ±3 days, in the current and other big-enough venues; rejects slots with venue conflicts/blackouts/closed hours; ranks by expected participation `show_rate × time_factor × (registered − 0.5 × clashing students)`. The time factor is learned from past turnout by start hour, or a documented default curve (labelled as fallback in the UI).

## Tests
```bash
cd backend && pytest -q          # AI unit tests + API tests (uses in-memory SQLite, no MySQL needed)
cd frontend && npm run build
```

## API overview (all under `/api`)
`POST /auth/register|login|logout`, `GET /auth/me` · `GET /events`, `GET /events/:id`, `POST/PUT/DELETE /events`, `POST /events/:id/publish|cancel|register`, `GET /events/:id/optimize|registrations`, `PUT /events/:id/attendance` · `GET/POST/PUT /clubs`, `/clubs/:id/join|members|activities` · `GET/POST/PUT/DELETE /venues`, `/venues/:id/availability|blackouts`, `POST /venues/check` · `GET /me/dashboard`, `/coordinator/dashboard` · `/admin/*` · `/reports/participation|clubs|venues|timeline` · `GET /ai/conflicts`, `POST /ai/predict` · `GET /stats`.

## Notes
* No external service credentials are required. Fonts load from Google Fonts when online and fall back to Georgia/system fonts offline.
* Set a strong `SECRET_KEY` before deploying. Demo passwords are for local use only.
* Notifications are in-app (stored in the database); there is no email/SMS integration.
* All people, emails and events in the seed data are fictional.
