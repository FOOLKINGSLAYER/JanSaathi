import json
import os
import threading
from datetime import date

from werkzeug.security import generate_password_hash

from models import User


def load_local_env():
    path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_local_env()

try:
    from libsql_experimental import connect
except ImportError:
    connect = None

DEMO_PASSWORD = "JanSaathi@123"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@jansaathi.in").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", DEMO_PASSWORD)


def _client():
    url, token = os.getenv("TURSO_DATABASE_URL"), os.getenv("TURSO_AUTH_TOKEN")
    if not connect or not url or not token:
        return None
    client = _TursoClient(connect(url, auth_token=token))
    _ensure_core_tables(client)
    _ensure_ai_tables(client)
    return client


class _QueryResult:
    def __init__(self, cursor):
        self.columns = [column[0] for column in (cursor.description or [])]
        self.rows = cursor.fetchall() if cursor.description else []
        self.last_insert_rowid = cursor.lastrowid


class _TursoClient:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        return _QueryResult(self.connection.execute(query, parameters))

    def commit(self):
        self.connection.commit()


_ai_tables_ready = set()
_ai_tables_lock = threading.Lock()

_core_tables_ready = set()
_core_tables_lock = threading.Lock()


def _ensure_core_tables(client):
    key = os.getenv("TURSO_DATABASE_URL", "")
    if key in _core_tables_ready:
        return
    with _core_tables_lock:
        if key in _core_tables_ready:
            return
        client.execute("CREATE TABLE IF NOT EXISTS organizations (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, type TEXT NOT NULL, location TEXT NOT NULL DEFAULT 'India', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        client.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK (role IN ('citizen', 'university', 'industry', 'government', 'admin')), organization_id INTEGER REFERENCES organizations(id), active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        try:
            client.execute("ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
        except Exception:
            pass
        client.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        client.commit()
        _seed_demo_users(client)
        _sync_admin_user(client)
        _core_tables_ready.add(key)


def _seed_demo_users(client):
    rows = _row_dict(client.execute("SELECT id FROM users LIMIT 1"))
    if rows:
        return
    password_hash = generate_password_hash(DEMO_PASSWORD)
    demo_users = [
        ("Aarav Sharma", "citizen@jansaathi.in", "citizen", None),
        ("Dr. Meera Iyer", "university@jansaathi.in", "university", "National Institute of Technology"),
        ("Rohan Mehta", "industry@jansaathi.in", "industry", "Sahaara Innovations"),
        ("Ananya Rao", "government@jansaathi.in", "government", "Department of Rural Development"),
        ("Platform Admin", ADMIN_EMAIL, "admin", "JanSaathi Platform"),
    ]
    for name, email, role, organization in demo_users:
        organization_id = None
        if organization:
            client.execute("INSERT OR IGNORE INTO organizations (name, type) VALUES (?, ?)", (organization, role))
            organization_rows = _row_dict(client.execute("SELECT id FROM organizations WHERE name = ?", (organization,)))
            organization_id = organization_rows[0]["id"] if organization_rows else None
        client.execute("INSERT INTO users (name, email, password_hash, role, organization_id) VALUES (?, ?, ?, ?, ?)", (name, email, password_hash, role, organization_id))
    client.commit()


def _sync_admin_user(client):
    rows = _row_dict(client.execute("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,)))
    password_hash = generate_password_hash(ADMIN_PASSWORD)
    if rows:
        client.execute("UPDATE users SET role = 'admin', password_hash = ?, active = 1 WHERE id = ?", (password_hash, rows[0]["id"]))
    else:
        client.execute("INSERT INTO users (name, email, password_hash, role, active) VALUES (?, ?, ?, 'admin', 1)", ("Platform Admin", ADMIN_EMAIL, password_hash))
    client.commit()


def _ensure_ai_tables(client):
    key = os.getenv("TURSO_DATABASE_URL", "")
    if key in _ai_tables_ready:
        return
    with _ai_tables_lock:
        if key in _ai_tables_ready:
            return
        client.execute("CREATE TABLE IF NOT EXISTS ai_analysis_cache (cache_key TEXT PRIMARY KEY, response_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        client.execute("CREATE TABLE IF NOT EXISTS ai_usage (usage_date TEXT PRIMARY KEY, request_count INTEGER NOT NULL DEFAULT 0)")
        client.commit()
        _ai_tables_ready.add(key)


def _row_dict(result):
    columns = [column[0] if isinstance(column, tuple) else column for column in result.columns]
    return [dict(zip(columns, row)) for row in result.rows]


def _fallback_users():
    password = generate_password_hash(DEMO_PASSWORD)
    admin_password = generate_password_hash(ADMIN_PASSWORD)
    return [
        User(1, "Aarav Sharma", "citizen@jansaathi.in", password, "citizen"),
        User(2, "Dr. Meera Iyer", "university@jansaathi.in", password, "university", "National Institute of Technology"),
        User(3, "Rohan Mehta", "industry@jansaathi.in", password, "industry", "Sahaara Innovations"),
        User(4, "Ananya Rao", "government@jansaathi.in", password, "government", "Department of Rural Development"),
        User(5, "Platform Admin", ADMIN_EMAIL, admin_password, "admin", "JanSaathi Platform"),
    ]


def get_demo_user_by_email(email: str) -> User | None:
    client = _client()
    if client:
        rows = _row_dict(client.execute("SELECT u.id, u.name, u.email, u.password_hash, u.role, u.active, COALESCE(o.name, '') AS organization FROM users u LEFT JOIN organizations o ON o.id = u.organization_id WHERE u.email = ? AND u.active = 1", (email,)))
        if rows:
            row = rows[0]
            return User(row["id"], row["name"], row["email"], row["password_hash"], row["role"], row["organization"])
        return None
    return next((user for user in _fallback_users() if user.email == email), None)


def _challenge(row):
    row["keywords"] = [item for item in (row.get("ai_keywords") or "").split(",") if item]
    row["evidence"] = row.get("evidence", 0)
    row["assigned_institution"] = row.get("assigned_institution") or "Pending review"
    row["stage"] = row.get("stage") or row.get("status", "SUBMITTED").replace("_", " ").title()
    return row


def get_challenge(challenge_id: int) -> dict | None:
    client = _client()
    if not client:
        return next((item for item in _fallback_challenges() if item["id"] == challenge_id), None)
    rows = _row_dict(client.execute("SELECT c.*, COALESCE(o.name, 'Pending review') AS assigned_institution, (SELECT COUNT(*) FROM challenge_media m WHERE m.challenge_id = c.id) AS evidence FROM challenges c LEFT JOIN challenge_assignments a ON a.challenge_id = c.id LEFT JOIN organizations o ON o.id = a.organization_id WHERE c.id = ? ORDER BY a.id DESC LIMIT 1", (challenge_id,)))
    return _challenge(rows[0]) if rows else None


def _fallback_challenges():
    return [{"id": 1, "title": "Affordable irrigation guidance for small farms", "description": "Farmers in our village struggle to determine when crops need irrigation. An affordable way to understand soil moisture could reduce water use and protect yields.", "submitted_by": 1, "category": "Agriculture", "location": "Nashik, Maharashtra", "status": "ASSIGNED", "priority": "Medium", "ai_summary": "Farmers lack an affordable system for determining optimal irrigation timing.", "keywords": ["irrigation", "soil moisture", "farming"], "created_at": "18 Aug 2026", "assigned_institution": "National Institute of Technology", "stage": "University evaluation", "evidence": 3}, {"id": 2, "title": "Reliable drinking water access in summer", "description": "The handpump near our community school runs dry every summer and residents walk several kilometres for clean drinking water.", "submitted_by": 1, "category": "Water", "location": "Beed, Maharashtra", "status": "UNDER_REVIEW", "priority": "High", "ai_summary": "A seasonal water shortage is affecting a rural school and nearby households.", "keywords": ["drinking water", "rural infrastructure", "sanitation"], "created_at": "12 Aug 2026", "assigned_institution": "Pending review", "stage": "Validation", "evidence": 2}]


def challenges_for_user(user_id: int) -> list[dict]:
    client = _client()
    if not client:
        return [item for item in _fallback_challenges() if item["submitted_by"] == user_id]
    rows = _row_dict(client.execute("SELECT c.*, COALESCE(o.name, 'Pending review') AS assigned_institution, (SELECT COUNT(*) FROM challenge_media m WHERE m.challenge_id = c.id) AS evidence FROM challenges c LEFT JOIN challenge_assignments a ON a.challenge_id = c.id LEFT JOIN organizations o ON o.id = a.organization_id WHERE c.submitted_by = ? GROUP BY c.id ORDER BY c.id DESC", (user_id,)))
    return [_challenge(row) for row in rows]


def add_challenge(title, description, category, location, submitted_by, analysis=None):
    client = _client()
    analysis = analysis or {}
    summary = analysis.get("summary") or description[:150].rstrip() + ("..." if len(description) > 150 else "")
    keywords = ",".join(analysis.get("keywords") or [category.lower(), "community need", "local innovation"])
    priority = analysis.get("priority", "Medium")
    stored_category = analysis.get("category") or category
    if client:
        result = client.execute("INSERT INTO challenges (title, description, submitted_by, category, location, status, priority, ai_summary, ai_keywords) VALUES (?, ?, ?, ?, ?, 'UNDER_REVIEW', ?, ?, ?)", (title, description, submitted_by, stored_category, location, priority, summary, keywords))
        client.commit()
        return get_challenge(result.last_insert_rowid)
    return {"id": 99, "title": title, "description": description, "submitted_by": submitted_by, "category": stored_category, "location": location, "status": "UNDER_REVIEW", "priority": priority, "ai_summary": summary, "keywords": keywords.split(","), "created_at": date.today().strftime("%d %b %Y"), "assigned_institution": "Pending review", "stage": "AI processing", "evidence": 0}


def get_ai_cache(cache_key):
    client = _client()
    if not client:
        return None
    rows = _row_dict(client.execute("SELECT response_json FROM ai_analysis_cache WHERE cache_key = ?", (cache_key,)))
    return json.loads(rows[0]["response_json"]) if rows else None


def save_ai_cache(cache_key, response):
    client = _client()
    if client:
        client.execute("INSERT OR REPLACE INTO ai_analysis_cache (cache_key, response_json) VALUES (?, ?)", (cache_key, json.dumps(response, ensure_ascii=True)))
        client.commit()


def reserve_ai_request(limit):
    client = _client()
    if not client:
        return True
    today = date.today().isoformat()
    rows = _row_dict(client.execute("SELECT request_count FROM ai_usage WHERE usage_date = ?", (today,)))
    count = rows[0]["request_count"] if rows else 0
    if count >= limit:
        return False
    client.execute("INSERT INTO ai_usage (usage_date, request_count) VALUES (?, 1) ON CONFLICT(usage_date) DO UPDATE SET request_count = request_count + 1", (today,))
    client.commit()
    return True


def add_user(name, email, password_hash, role, organization=""):
    client = _client()
    if client:
        organization_id = None
        if organization:
            client.execute("INSERT OR IGNORE INTO organizations (name, type, location) VALUES (?, ?, 'India')", (organization, role))
            rows = _row_dict(client.execute("SELECT id FROM organizations WHERE name = ?", (organization,)))
            organization_id = rows[0]["id"] if rows else None
        result = client.execute("INSERT INTO users (name, email, password_hash, role, organization_id, active) VALUES (?, ?, ?, ?, ?, 1)", (name, email, password_hash, role, organization_id))
        client.commit()
        return User(result.last_insert_rowid, name, email, password_hash, role, organization)
    return User(99, name, email, password_hash, role, organization)


def all_users():
    client = _client()
    if not client:
        return [{"id": user.id, "name": user.name, "email": user.email, "role": user.role, "active": 1, "created_at": "", "organization": user.organization} for user in _fallback_users()]
    return _row_dict(client.execute("SELECT u.id, u.name, u.email, u.role, u.active, u.created_at, COALESCE(o.name, '') AS organization FROM users u LEFT JOIN organizations o ON o.id = u.organization_id ORDER BY u.created_at DESC, u.id DESC"))


def user_count():
    client = _client()
    if not client:
        return len(_fallback_users())
    rows = _row_dict(client.execute("SELECT COUNT(*) AS total FROM users"))
    return rows[0]["total"] if rows else 0


def update_user(user_id, role=None, active=None):
    client = _client()
    if not client:
        return False
    updates, values = [], []
    if role in {"citizen", "university", "industry", "government", "admin"}:
        updates.append("role = ?")
        values.append(role)
    if active is not None:
        updates.append("active = ?")
        values.append(1 if active else 0)
    if not updates:
        return False
    values.append(user_id)
    client.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(values))
    client.commit()
    return True


def delete_user(user_id):
    client = _client()
    if not client:
        return False
    client.execute("DELETE FROM users WHERE id = ? AND role != 'admin'", (user_id,))
    client.commit()
    return True


def all_organizations():
    client = _client()
    if not client:
        return []
    return _row_dict(client.execute("SELECT o.id, o.name, o.type, o.location, COUNT(u.id) AS members FROM organizations o LEFT JOIN users u ON u.organization_id = o.id GROUP BY o.id ORDER BY o.name"))


def get_project(project_id):
    client = _client()
    if client:
        rows = _row_dict(client.execute("SELECT p.*, o.name AS organization, u.name AS faculty, (SELECT COUNT(*) FROM project_members pm WHERE pm.project_id = p.id) AS members FROM projects p JOIN organizations o ON o.id = p.organization_id LEFT JOIN project_members pm2 ON pm2.project_id = p.id LEFT JOIN users u ON u.id = pm2.user_id AND pm2.role = 'Faculty mentor' WHERE p.id = ? GROUP BY p.id", (project_id,)))
        if rows:
            row = rows[0]
            row.update({"progress": 58, "industry_partner": "Seeking technology partner", "domain": "Agricultural Engineering · IoT", "milestones": [("Research", "complete"), ("Prototype", "active"), ("Testing", "upcoming"), ("Validation", "upcoming"), ("Deployment", "upcoming")]})
            return row
        return None
    return {"id": 1, "challenge_id": 1, "title": "JalMitra: low-cost soil moisture intelligence", "description": "A field-tested soil moisture kit and advisory service designed with smallholder farmers.", "organization": "National Institute of Technology", "faculty": "Dr. Meera Iyer", "status": "PROTOTYPE", "progress": 58, "target_date": "30 Nov 2026", "industry_partner": "Seeking technology partner", "domain": "Agricultural Engineering · IoT", "members": 8, "milestones": [("Research", "complete"), ("Prototype", "active"), ("Testing", "upcoming"), ("Validation", "upcoming"), ("Deployment", "upcoming")]}


def challenge_project(challenge_id):
    client = _client()
    if client:
        rows = _row_dict(client.execute("SELECT id FROM projects WHERE challenge_id = ? LIMIT 1", (challenge_id,)))
        return get_project(rows[0]["id"]) if rows else None
    return get_project(1) if challenge_id == 1 else None


def all_challenges():
    client = _client()
    if client:
        rows = _row_dict(client.execute("SELECT c.*, COALESCE(o.name, 'Pending review') AS assigned_institution, (SELECT COUNT(*) FROM challenge_media m WHERE m.challenge_id = c.id) AS evidence FROM challenges c LEFT JOIN challenge_assignments a ON a.challenge_id = c.id LEFT JOIN organizations o ON o.id = a.organization_id GROUP BY c.id ORDER BY c.id DESC"))
        return [_challenge(row) for row in rows]
    return _fallback_challenges()


def dashboard_metrics():
    client = _client()
    if client:
        counts = {row["table_name"]: row["total"] for row in _row_dict(client.execute("SELECT 'challenges' AS table_name, COUNT(*) AS total FROM challenges UNION ALL SELECT 'projects', COUNT(*) FROM projects UNION ALL SELECT 'organizations', COUNT(*) FROM organizations"))}
        return {"challenges": counts.get("challenges", 0), "projects": counts.get("projects", 0), "universities": counts.get("organizations", 0), "deployed": 0, "citizens": 0}
    return {"challenges": 24, "projects": 8, "universities": 18, "deployed": 12, "citizens": 640}


def update_challenge_status(challenge_id, status, stage, institution=None):
    client = _client()
    if client:
        client.execute("UPDATE challenges SET status = ? WHERE id = ?", (status, challenge_id))
        if institution:
            rows = _row_dict(client.execute("SELECT id FROM organizations WHERE name = ?", (institution,)))
            if rows:
                client.execute("INSERT INTO challenge_assignments (challenge_id, organization_id, status) VALUES (?, ?, 'ASSIGNED')", (challenge_id, rows[0]["id"]))
        client.commit()


def add_collaboration(project_id, organization_name, collaboration_type):
    client = _client()
    if client:
        rows = _row_dict(client.execute("SELECT id FROM organizations WHERE name = ?", (organization_name,)))
        organization_id = rows[0]["id"] if rows else None
        if organization_id:
            client.execute("INSERT INTO collaborations (project_id, organization_id, type, status) VALUES (?, ?, ?, 'PENDING')", (project_id, organization_id, collaboration_type))
            client.commit()
