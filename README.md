# Qatar Foundation — Admin Portal

A professional full-stack admin portal with a Flask REST API backend and a single-page HTML frontend.

---

## 📁 Project Structure

```
qf-admin-portal/
├── backend/
│   ├── app.py            ← Flask app + all API routes
│   ├── models.py         ← SQLAlchemy ORM models
│   ├── config.py         ← Configuration (JWT, DB, CORS)
│   ├── extensions.py     ← Flask extension instances
│   ├── requirements.txt
│   └── database.db       ← Auto-created on first run
│
└── frontend/
    └── index.html        ← Single-page application
```

---

## 🚀 Quick Start

### 1. Backend

```bash
cd backend

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
python app.py
# ✅  Running at http://localhost:5000
```

### 2. Frontend

Open `frontend/index.html` directly in your browser, or serve it:

```bash
# Using Python's built-in server (from frontend/)
cd frontend
python -m http.server 8080
# ✅  Open http://localhost:8080
```

> **CORS** is pre-configured — the backend accepts requests from any origin.

---

## 🔑 API Reference

All protected routes require the `Authorization: Bearer <token>` header.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/signup` | ❌ | Register a new admin |
| POST | `/login` | ❌ | Login + receive JWT |
| POST | `/forgot-password` | ❌ | Request password reset link |
| POST | `/reset-password/<token>` | ❌ | Reset password with token |
| GET | `/opportunities` | ✅ | List your opportunities |
| POST | `/opportunities` | ✅ | Create an opportunity |
| PUT | `/opportunities/<id>` | ✅ | Update an opportunity |
| DELETE | `/opportunities/<id>` | ✅ | Delete an opportunity |
| GET | `/health` | ❌ | API health check |

---

## ✅ Test Flow

1. Open `frontend/index.html`
2. Click **Create one** → register an admin account
3. You're automatically logged in to the dashboard
4. Use **Add Opportunity** to create entries
5. Logout and sign back in — data persists in SQLite

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `qf-admin-super-secret-key-2024` | Flask secret |
| `JWT_SECRET_KEY` | `qf-jwt-secret-key-2024` | JWT signing key |
| `DATABASE_URL` | `sqlite:///database.db` | Database URI |

For production, set strong secrets via environment variables.
