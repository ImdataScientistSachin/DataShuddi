"""
DataShuddi -- Development Environment Bootstrap and Validator.

Verifies local folder structure, checks for .env file,
and validates Ollama service availability and required models.
"""
import shutil
from pathlib import Path
from typing import Any

httpx: Any = None
try:
    import httpx as _httpx
    httpx = _httpx
except ImportError:
    httpx = None

ROOT_DIR = Path(__file__).resolve().parent.parent

REQUIRED_DIRS = [
    "src/agent/nodes",
    "src/utils",
    "streamlit_app/app_pages",
    "streamlit_app/assets",
    "tests/unit",
    "tests/integration",
    "tests/fixtures/sample_docs",
    "tests/fixtures/sample_responses",
    "tests/fixtures/expected_outputs",
    "data/raw",
    "data/clean",
    "data/human_review",
    "data/temp",
    "data/qdrant_storage",
    "data/postgres_data",
    "scripts",
    "adr",
    "notebooks",
    "docs",
]

REQUIRED_MODELS = [
    "qwen2.5-coder:3b",
    "qwen2.5-coder:14b",
    "mxbai-embed-large",
]


def check_directories() -> bool:
    """Ensure all required project directories exist."""
    print("[DIRS] Checking directory structure...")
    all_ok = True
    for rel_path in REQUIRED_DIRS:
        d = ROOT_DIR / rel_path
        if not d.exists():
            print(f"  [CREATING] {rel_path}")
            d.mkdir(parents=True, exist_ok=True)
        else:
            print(f"  [OK] {rel_path}")
    return all_ok


def check_env_file() -> bool:
    """Check if .env exists; copy from .env.example if missing."""
    print("\n[ENV] Checking .env configuration...")
    env_path = ROOT_DIR / ".env"
    env_example = ROOT_DIR / ".env.example"

    if not env_path.exists():
        if env_example.exists():
            print("  [COPYING] .env.example -> .env")
            shutil.copy(env_example, env_path)
        else:
            print("  [ERROR] Neither .env nor .env.example found.")
            return False
    else:
        print("  [OK] .env exists")
    return True


def check_ollama() -> bool:
    """Check if Ollama is reachable and has the required models."""
    print("\n[OLLAMA] Checking local Ollama server...")

    if httpx is None:
        print("  [SKIP] httpx not installed. Cannot check Ollama.")
        return False

    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        if resp.status_code != 200:
            print(f"  [WARNING] Ollama returned status {resp.status_code}.")
            return False

        models_data = resp.json().get("models", [])
        installed = [m.get("name", "") for m in models_data]
        print(f"  Installed models: {installed}")

        for req in REQUIRED_MODELS:
            found = any(req in name for name in installed)
            if found:
                print(f"  [OK] {req}")
            else:
                print(f"  [MISSING] {req} -- run: ollama pull {req}")

        return True

    except Exception as exc:
        print(f"  [WARNING] Ollama connection failed: {exc}")
        print("  Ensure Ollama is running on http://localhost:11434")
        return False


def main() -> None:
    """Run all bootstrap checks."""
    print("=" * 60)
    print("  DataShuddi -- Environment Bootstrap & Health Check")
    print("=" * 60)

    dirs_ok = check_directories()
    env_ok = check_env_file()
    ollama_ok = check_ollama()

    print("\n" + "=" * 60)
    if dirs_ok and env_ok:
        print("[PASS] Environment setup verification complete.")
    else:
        print("[FAIL] Environment setup encountered issues.")
    if not ollama_ok:
        print("[INFO] Ollama check skipped or failed. Non-blocking.")
    print("=" * 60)


if __name__ == "__main__":
    main()
