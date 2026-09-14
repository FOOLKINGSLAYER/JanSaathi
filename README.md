# JanSaathi

Minimal Flask prototype for the Societal Innovation Collaboration Portal.

## Run locally

Install the Python dependencies, then start the Flask app:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000/login`.

The local `.env` file contains configuration placeholders and is ignored by Git. Turso and Gemini keys are not required to explore the portal locally. When Turso is enabled, the app creates the `organizations` and `users` tables on first connection. User passwords are stored only as Werkzeug password hashes in `users.password_hash`; plaintext passwords are never persisted.

When those integrations are enabled, add the values directly to `.env` and never commit real secrets:

```env
TURSO_DATABASE_URL=libsql://your-database.turso.io
TURSO_AUTH_TOKEN=your-token
GEMINI_API_KEY=your-key
ADMIN_EMAIL=admin@jansaathi.in
ADMIN_PASSWORD=your-long-admin-password
```

## Prototype login

Use `citizen@jansaathi.in` with `JanSaathi@123`. On a fresh Turso database, the app seeds the demo accounts with hashed passwords. Without Turso, equivalent demo users are provided by the in-memory fallback.

Additional demo roles are available with the same password:

- `university@jansaathi.in`
- `industry@jansaathi.in`
- `government@jansaathi.in`

The admin account is synchronized from `ADMIN_EMAIL` and `ADMIN_PASSWORD`. Its password is hashed before storage in `users.password_hash`. Admins can review challenge statuses, change account roles, enable or disable accounts, and delete non-admin accounts from the control room.

## Structure

- `app.py`: Flask routes, sessions, login handling, and role redirects
- `database.py`: Turso schema initialization and data access
- `ai_service.py`: cached Gemini analysis with local fallback and daily budget guard
- `models.py`: prototype user model
- `templates/layout.html`: shared HTML shell and asset references
- `templates/login.html`: login page content only
- `static/styles.css`: shared styles
- `static/javascript.js`: shared browser behavior

## Demo roles

The portal currently includes working public pages, registration, citizen challenge submission/detail, university discovery/evaluation/project workspace, industry opportunities/collaboration interest, government monitoring/analytics, and admin review views. Authentication and registered users persist in Turso when configured; other prototype data uses the repository functions in `database.py` and local fallback data when Turso is unavailable.

## AI usage controls

Gemini is called only when a new challenge is submitted. The service:

- hashes the normalized challenge content and checks the persistent `ai_analysis_cache` table first;
- stores the category, priority, summary, keywords and domains after a successful analysis;
- enforces `GEMINI_DAILY_REQUEST_LIMIT` through the Turso `ai_usage` table, defaulting to 20 requests per day;
- uses a deterministic local summary and keyword fallback when Gemini is unavailable, over quota, or returns invalid data.

Configure the optional controls in `.env`:

```env
GEMINI_MODEL=gemini-2.0-flash-lite
GEMINI_DAILY_REQUEST_LIMIT=20
```