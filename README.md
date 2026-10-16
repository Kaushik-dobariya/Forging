# Industrial Forging & Precision Engineering CMS

A production-ready, modular CMS-driven corporate website, product catalog, lead generation engine, and SEO platform engineered for high-precision forging and manufacturing enterprises.

---

## 1. Architectural Highlights (Phase 1 Foundation)

* **Backend**: Python 3.14+ with FastAPI modular architecture.
* **Database Engine**: SQLAlchemy 2.0 ORM switchable between SQLite (local dev) and MySQL (production).
* **Schema Migrations**: Alembic automated migration pipeline.
* **Frontend Templating**: Jinja2 with semantic HTML5, modern CSS custom properties, and responsive layout.
* **Design Identity**: Industrial + Premium Engineering (Deep Slate `#17212B`, Graphite `#28323C`, Warm Copper `#B7793F`, Off-White `#F5F4F0`).
* **Authentication & Security**:
  * Bcrypt password hashing with password policy validator.
  * Tamper-proof HTTP-only signed session cookies with SameSite controls.
  * Brute-force protection with account lockout after 5 consecutive failed attempts.
  * Role-Based Access Control (Super Admin, Admin, Editor).
  * CSRF validation architecture and constant-time verification.
  * Security headers middleware (`X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`).
  * File upload validation pipeline with MIME type verification and Pillow raster integrity checks.
* **Structured Logging**: Automatic scrubbing/redaction of passwords, tokens, cookies, and secrets.
* **Test Suite**: 100% automated test coverage for startup, health checks, authentication, lockout, public views, and upload validation.

---

## 2. Directory Structure

```
forging-cms/
├── app/
│   ├── main.py                  # Application factory, lifespan, security middleware, and exception handlers
│   ├── cli.py                   # Administrative CLI tool (create-superadmin, etc.)
│   ├── core/
│   │   ├── config.py            # Pydantic Settings environment configuration
│   │   ├── database.py          # SQLAlchemy engine, session maker, base model, SQLite/MySQL switch
│   │   ├── security.py          # Bcrypt hashing, session signing, CSRF tokens, lockout thresholds
│   │   ├── permissions.py       # RBAC role definitions and permission gates
│   │   ├── templates.py         # Jinja2 template engine configuration and global helpers
│   │   └── logging.py           # Structured logging with sensitive data redaction
│   ├── models/
│   │   ├── __init__.py          # Model exports
│   │   └── user.py              # User entity with RBAC, attempt tracking, and lockout methods
│   ├── schemas/
│   │   ├── __init__.py          # Pydantic schema exports
│   │   └── user.py              # User request/response schemas, validation models
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── user_repository.py   # Isolated database persistence operations
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Authentication, session creation, lockout management
│   │   └── upload_service.py    # File upload validation, Pillow verification, sanitization
│   ├── api/
│   │   ├── __init__.py          # API router
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── routes.py        # /api/v1 endpoints (health, profile)
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── dependencies.py      # Admin session & superadmin authorization dependencies
│   │   └── routes.py            # Admin views (/admin/login, /admin/logout, /admin dashboard)
│   ├── web/
│   │   ├── __init__.py
│   │   └── routes.py            # Public website views (/)
│   ├── templates/
│   │   ├── base.html            # Master layout
│   │   ├── components/          # Reusable components (header, footer, alerts)
│   │   ├── public/              # Public web templates (index.html, errors/)
│   │   └── admin/               # Super admin templates (login.html, dashboard.html, errors/)
│   ├── static/
│   │   ├── css/                 # theme.css (tokens), public.css, admin.css
│   │   ├── js/                  # main.js, admin.js
│   │   ├── images/
│   │   └── fonts/
│   └── utils/
├── migrations/
│   ├── env.py                   # Alembic environment with SQLite batch mode & model metadata
│   ├── script.py.mako           # Revision template
│   └── versions/                # Generated version scripts
├── tests/
│   ├── conftest.py              # Test database, transactional sessions, test client
│   ├── test_auth.py             # Auth flows, passwords, lockout, sessions
│   ├── test_health.py           # Startup, /health, /api/v1/health, headers, homepage
│   └── test_errors_and_uploads.py # 404 handlers, upload MIME & Pillow validation
├── uploads/                     # Upload directory (tracked via .gitkeep)
├── .env.example                 # Environment configuration template
├── .env                         # Local environment settings
├── alembic.ini                  # Alembic migration configuration
├── requirements.txt             # Pinned project dependencies
└── README.md                    # System documentation
```

---

## 3. Prerequisites & Environment Setup

### Prerequisites
* **Python**: 3.10+ (Tested and verified on Python `3.14.0`)
* **Operating System**: Windows / Linux / macOS

### Setup Virtual Environment
```bash
# Clone or open the repository
cd Forging

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Environment Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Key environment parameters:
* `APP_ENV`: `development` | `staging` | `production`
* `APP_DEBUG`: `true` | `false`
* `SECRET_KEY`: High-entropy cryptographic string for session tokens (min 32 chars).
* `DATABASE_URL`:
  * **Development (SQLite)**: `sqlite:///./forging.db`
  * **Production (MySQL)**: `mysql+pymysql://username:password@hostname:3306/forging_cms?charset=utf8mb4`
* `UPLOAD_DIR`: `./uploads`
* `MAX_UPLOAD_SIZE`: `10485760` (10MB in bytes)
* `FIRST_SUPERADMIN_EMAIL`: Default bootstrap administrator email.
* `FIRST_SUPERADMIN_PASSWORD`: Default bootstrap administrator password.
* `DISABLE_SQLALCHEMY_CEXT`: `1` (ensures pure-Python SQLAlchemy operation where OS policies restrict unsigned DLLs).

---

## 5. Database Migrations

Run database migrations to initialize or update the schema:
```bash
# Upgrade database to latest revision
alembic upgrade head

# Generate a new migration revision after modifying models
alembic revision --autogenerate -m "describe_changes"
```

---

## 6. Super Admin Account Creation

You can create or bootstrap a Super Admin using the CLI command:

```bash
# Interactive prompt:
python -m app.cli create-superadmin

# Or passing flags:
python -m app.cli create-superadmin --email admin@forgingcms.com --password "Admin@123456" --name "Super Administrator"
```

*Note: On application boot, if `FIRST_SUPERADMIN_EMAIL` and `FIRST_SUPERADMIN_PASSWORD` are configured and no superadmin exists yet, the application will automatically bootstrap the initial administrator.*

---

## 7. Running the Development Server

Start the application with Uvicorn:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

* Public Website: [http://localhost:8000/](http://localhost:8000/)
* Super Admin Login: [http://localhost:8000/admin/login](http://localhost:8000/admin/login)
* Super Admin Console: [http://localhost:8000/admin](http://localhost:8000/admin)
* Health Status Endpoint: [http://localhost:8000/health](http://localhost:8000/health)
* API v1 Health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
* Interactive API Docs (Debug mode): [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 8. Running the Automated Test Suite

Execute the test suite with pytest:
```bash
pytest -v
```

All 16 test cases cover:
* Database connection check
* Health endpoints (`/health`, `/api/v1/health`)
* Public homepage rendering & design elements
* Security headers middleware
* Bcrypt hashing & verification
* Password strength validation
* Signed tamper-proof session tokens
* Unauthenticated redirection to login
* Successful Super Admin login & dashboard view
* Invalid credential rejection & feedback
* Session termination (logout)
* 5-attempt brute-force account lockout
* Public & Admin 404 error handlers
* File upload validation (MIME type & Pillow raster verification)
*