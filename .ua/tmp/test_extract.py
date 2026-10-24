import json
import subprocess
from pathlib import Path

project_root = Path("G:/Project Directory/GENAI PROJECT DIRECTORY/DataShuddi")
skill_dir = Path("C:/Users/demog/.gemini/config/skills/understand-anything/repo/understand-anything-plugin/skills/understand")

input_data = {
    "projectRoot": str(project_root),
    "batchFiles": [
        {"path": "src/agent/graph.py", "language": "python", "sizeLines": 144, "fileCategory": "code"},
        {"path": "src/agent/state.py", "language": "python", "sizeLines": 114, "fileCategory": "code"}
    ],
    "batchImportData": {
        "src/agent/graph.py": ["src/agent/state.py", "src/agent/checkpoints.py"]
    }
}

test_in = project_root / ".ua/tmp/test-extract-in.json"
test_out = project_root / ".ua/tmp/test-extract-out.json"

with open(test_in, "w", encoding="utf-8") as f:
    json.dump(input_data, f, indent=2)

cmd = ["node", str(skill_dir / "extract-structure.mjs"), str(test_in), str(test_out)]
res = subprocess.run(cmd, capture_output=True, text=True)
print("Returncode:", res.returncode)
if res.stderr:
    print("Stderr:", res.stderr[:500])

if test_out.exists():
    with open(test_out, "r", encoding="utf-8") as f:
        data = json.load(f)
        print("Keys:", data.keys())
        print("Analyzed:", data.get("filesAnalyzed"))
        if data.get("results"):
            print("First result keys:", data["results"][0].keys())
            print("First result symbols:", [s.get("name") for s in data["results"][0].get("symbols", [])])
