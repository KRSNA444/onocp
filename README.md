# ONOCP — One Nation, One Complaint Portal

A working prototype: citizens submit complaints, the system auto-detects
category and routes to the right department, tracks status against an
SLA, and shows a public heatmap. Includes an admin dashboard.

## Stack
- **Backend**: FastAPI + SQLite (SQLAlchemy)
- **Frontend**: single HTML file (vanilla JS + Leaflet map), no build step

## Run it

### 1. Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
API runs at `http://127.0.0.1:8000` — interactive docs at `http://127.0.0.1:8000/docs`.

### 2. Frontend
Just open `frontend/index.html` directly in a browser (double-click it,
or use VS Code's "Live Server" extension). It talks to the backend at
`127.0.0.1:8000` — make sure the backend is running first.

## How the smart routing works
`backend/routing.py` has a `CATEGORY_CONFIG` dict — each category maps to
a department, an SLA (in days), a color (used in the UI/heatmap), and a
keyword list. `detect_category()` scores complaint text against these
keywords and picks the best match. This is intentionally simple so you
can swap it for a real ML/embeddings classifier later (e.g. sentence
embeddings + cosine similarity against category descriptions, or a
fine-tuned small model) without touching any other part of the app.

## What's implemented
- Complaint submission with title, description, map-based location pick
- Auto category detection → department routing → SLA deadline
- Public tracking by Tracking ID (e.g. `ONOCP-AB12CD`)
- Status flow: Pending → Assigned → In Progress → Resolved
- Auto-escalation flag when a complaint passes its SLA deadline unresolved
- Admin dashboard: stats, filters, inline status updates
- Public heatmap (Leaflet) colored by complaint category

## Natural next steps (good for your report / future milestones)
1. **Auth**: admin login (JWT) so the dashboard isn't open to everyone
2. **Photo upload**: accept an image with the complaint (store in
   `/uploads`, save the path on the `Complaint` row — the model field
   is easy to add)
3. **Real category detection**: replace keyword matching with a small
   ML classifier trained on labeled complaint text (you already have
   experience with Sentence Transformers from the Resume Screener —
   same idea applies here: embed complaint text, compare to category
   embeddings)
4. **Notifications**: SMS/email/WhatsApp when status changes (Twilio /
   WhatsApp Cloud API)
5. **Geocoding**: auto-convert `location_text` (e.g. "Sector 12,
   Delhi") to lat/lng via a free geocoding API, so citizens don't have
   to click the map manually
6. **Deploy**: backend → Render/Railway (SQLite → switch to Postgres
   for production), frontend → Netlify/Vercel — same pattern you used
   for your 3D site and Resume Screener
