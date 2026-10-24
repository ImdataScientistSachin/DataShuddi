import json
import subprocess
from pathlib import Path

project_root = Path("G:/Project Directory/GENAI PROJECT DIRECTORY/DataShuddi")
skill_dir = Path("C:/Users/demog/.gemini/config/skills/understand-anything/repo/understand-anything-plugin/skills/understand")

raw_scan_path = project_root / ".ua/intermediate/scan-raw.json"
with open(raw_scan_path, "r", encoding="utf-8") as f:
    raw_scan = json.load(f)

# Filter out test binaries, virtualenvs, cache, etc.
valid_files = []
for file_info in raw_scan.get("files", []):
    p = file_info["path"]
    if p.startswith(".venv") or p.startswith(".git") or p.startswith(".mypy_cache") or p.startswith(".pytest_cache") or p.startswith(".ruff_cache") or p.startswith(".ua"):
        continue
    valid_files.append(file_info)

import_input_path = project_root / ".ua/tmp/import-input.json"
import_output_path = project_root / ".ua/tmp/import-output.json"

with open(import_input_path, "w", encoding="utf-8") as f:
    json.dump({
        "projectRoot": str(project_root),
        "files": valid_files
    }, f, indent=2)

cmd = [
    "node",
    str(skill_dir / "extract-import-map.mjs"),
    str(import_input_path),
    str(import_output_path)
]

print("Running extract-import-map.mjs...")
res = subprocess.run(cmd, capture_output=True, text=True)
print("Returncode:", res.returncode)
if res.stderr:
    print("Stderr:", res.stderr[:500])

import_map = {}
if import_output_path.exists():
    with open(import_output_path, "r", encoding="utf-8") as f:
        out_data = json.load(f)
        import_map = out_data.get("importMap", {})

scan_result = {
    "name": "DataShuddi",
    "description": "Enterprise-grade, local-first, self-correcting PII scrubbing and data validation agent using LangGraph and Presidio.",
    "languages": ["python", "markdown", "dockerfile", "yaml", "toml"],
    "frameworks": ["LangGraph", "FastAPI", "Pydantic", "Presidio", "Streamlit", "Qdrant", "PyMuPDF"],
    "files": valid_files,
    "totalFiles": len(valid_files),
    "importMap": import_map,
    "complexity": "moderate"
}

scan_result_path = project_root / ".ua/intermediate/scan-result.json"
with open(scan_result_path, "w", encoding="utf-8") as f:
    json.dump(scan_result, f, indent=2)

print(f"Generated scan-result.json with {len(valid_files)} files and {len(import_map)} import map entries.")
