"""Root entrypoint for running the Forging CMS application."""
import os
import sys

from pathlib import Path

_ROOT_DIR = Path(__file__).resolve().parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

# Ensure required environment variables
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  FORGING CMS & PRECISION ENGINEERING PLATFORM")
    print("=" * 60)
    print("  Public Website:  http://127.0.0.1:8000  (or http://localhost:8000)")
    print("  Admin Portal:    http://127.0.0.1:8000/admin")
    print("  Admin Login:     http://127.0.0.1:8000/admin/login")
    print("  Default Admin:   admin@forgingcms.com / Admin@123456")
    print("=" * 60 + "\n", flush=True)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
