# Hospital Emergency Management System

A small Flask + SQLite web app for running an emergency department: register incoming patients, triage them by urgency, assign beds, and track each patient through treatment, admission or discharge.

## Features

- **Dashboard** with live counters (waiting, in treatment, critical, free beds, arrivals today)
- **Patient registration** with 5-level triage (1 Resuscitation to 5 Non-Urgent)
- **Priority queue** sorted by triage level, then waiting time
- **Bed board** showing which Emergency, Trauma and ICU beds are free or occupied
- **Bed assignment**, admit and discharge actions (beds are released automatically)
- **Patient records** page with search, status filter, editable notes and delete
- JSON endpoint at `/api/stats`

## Project structure

```
app.py            Flask routes
database.py       SQLite helpers, schema and demo data
base.html         Shared layout
index.html        Dashboard
patients.html     Patient records
style.css         Styling
requirements.txt  Python dependencies
Procfile          Process definition (gunicorn)
render.yaml       Render.com deployment config
```

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000. The database (`hospital.db`) and demo data are created automatically on first run.

## Deploy on Render

Push the repo to GitHub, create a new Blueprint on Render and point it at the repo. `render.yaml` configures the build and start commands.

Note: on Render's free plan the filesystem is ephemeral, so data resets on redeploy. Attach a persistent disk and set `DATABASE_PATH` for permanent storage.

## Environment variables

| Name | Purpose | Default |
|------|---------|---------|
| `SECRET_KEY` | Flask session/flash secret | dev value |
| `DATABASE_PATH` | SQLite file location | `hospital.db` next to `app.py` |
| `PORT` | Port for `python app.py` | `5000` |

## Disclaimer

Educational demo. Not certified for real clinical use.
