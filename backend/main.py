"""Entrypoint wrapper allowing uvicorn to run from inside backend/ directory directly."""
import sys
from pathlib import Path

# Add project root and backend directory to sys.path
_current_dir = Path(__file__).resolve().parent
_root_dir = _current_dir.parent
for _p in [str(_root_dir), str(_current_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Also expose a symlink-like alias for 'backend' module if not found
if "backend" not in sys.modules:
    import types
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [str(_current_dir)]
    sys.modules["backend"] = backend_pkg

from backend.app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
