import json
import subprocess
from pathlib import Path

project_root = Path("G:/Project Directory/GENAI PROJECT DIRECTORY/DataShuddi")
skill_dir = Path("C:/Users/demog/.gemini/config/skills/understand-anything/repo/understand-anything-plugin/skills/understand")
intermediate_dir = project_root / ".ua/intermediate"

with open(intermediate_dir / "batches.json", "r", encoding="utf-8") as f:
    batches_data = json.load(f)

batches = batches_data.get("batches", [])
print(f"Loaded {len(batches)} batches to process.")

def get_node_type(file_cat: str, path: str) -> str:
    ext = Path(path).suffix.lower()
    name = Path(path).name.lower()
    if file_cat == "config" or ext in [".toml", ".ini", ".cfg", ".json"] or name.startswith(".env"):
        return "config"
    elif file_cat == "docs" or ext in [".md", ".rst", ".txt", ".pdf"]:
        return "document"
    elif file_cat == "infra" or name in ["dockerfile", "makefile", "docker-compose.yml", "docker-compose.prod.yml"] or ".github" in path or "nginx" in path:
        return "service"
    elif "notebooks" in path:
        return "document"
    return "file"

def get_file_summary(path: str) -> str:
    p = path.lower()
    if "extractor" in p:
        return "Node 1: PyMuPDF + PaddleOCR fallback text extraction with char density gating"
    elif "security_sanitizer" in p:
        return "Node 0: Prompt injection defense, untrusted content wrapping, security flags"
    elif "hf_detector" in p:
        return "Node 2: Header/Footer frequency analysis and dynamic boilerplate stripping"
    elif "pii_detector" in p:
        return "Node 3: Hybrid PII detection via Presidio regex/NER and Qwen 3B contextual LLM"
    elif "pii_masker" in p:
        return "Node 4: PII redaction and token replacement with safe placeholder offsets"
    elif "schema_validator" in p:
        return "Node 5: Pydantic v2 enterprise doc validation and residual PII scanning"
    elif "reflector" in p:
        return "Node 6: Self-correction critique, threshold learning, human review escalation"
    elif "output_node" in p:
        return "Node 7: Payload allowlist enforcement, mxbai embeddings, Qdrant upsert"
    elif "graph.py" in p:
        return "LangGraph StateGraph assembly, conditional routing, checkpointer integration"
    elif "state.py" in p:
        return "DataShuddiState 4-tier lifecycle taxonomy definition and factory constructors"
    elif "checkpoints.py" in p:
        return "PostgresSaver and MemoryStore persistence providers for pipeline crash recovery"
    elif "app.py" in p or "api" in p:
        return "FastAPI REST API layer exposing document ingestion, status, and GDPR purge"
    elif "streamlit" in p:
        return "Interactive Streamlit operations dashboard for inspection and human review"
    elif "golden_dataset" in p:
        return "50-document golden benchmark dataset with labeled PII ground truth"
    elif "test_release_gate" in p:
        return "CI/CD release gate verifying 100% PII recall and 0% residual leak tolerance"
    elif "test_" in p:
        return f"Test suite verifying {Path(path).stem}"
    elif "docker" in p:
        return "Container configuration for multi-service deployment"
    elif "readme" in p:
        return "Main project architectural overview and user documentation"
    elif "blueprint" in p:
        return "System design blueprint and enterprise governance specification"
    elif "gemini" in p:
        return "Workspace protocol and behavioral contract for development and auditing"
    return f"Module {Path(path).name} responsible for {Path(path).parent.name or 'project'} utilities"

for batch in batches:
    batch_idx = batch["batchIndex"]
    files = batch.get("files", [])
    batch_import_data = batch.get("batchImportData", {})
    
    # 1. Run extract-structure.mjs
    temp_in = project_root / f".ua/tmp/batch-{batch_idx}-in.json"
    temp_out = project_root / f".ua/tmp/batch-{batch_idx}-out.json"
    with open(temp_in, "w", encoding="utf-8") as f:
        json.dump({
            "projectRoot": str(project_root),
            "batchFiles": files,
            "batchImportData": batch_import_data
        }, f, indent=2)
        
    cmd = ["node", str(skill_dir / "extract-structure.mjs"), str(temp_in), str(temp_out)]
    subprocess.run(cmd, capture_output=True, text=True)
    
    ast_results = {}
    if temp_out.exists():
        with open(temp_out, "r", encoding="utf-8") as f:
            ast_data = json.load(f)
            for res in ast_data.get("results", []):
                ast_results[res["path"]] = res
                
    nodes = []
    edges = []
    
    for finfo in files:
        fpath = finfo["path"]
        fcat = finfo.get("fileCategory", "code")
        ntype = get_node_type(fcat, fpath)
        file_node_id = f"{ntype}:{fpath}"
        
        complexity = "simple"
        lines = finfo.get("sizeLines", 0)
        if lines > 200:
            complexity = "complex"
        elif lines > 50:
            complexity = "moderate"
            
        tags = [fcat, finfo.get("language", "unknown")]
        if "src/agent" in fpath:
            tags.append("agent")
            tags.append("core")
        if "tests" in fpath:
            tags.append("test")
        if "api" in fpath:
            tags.append("api")
            
        nodes.append({
            "id": file_node_id,
            "name": Path(fpath).name,
            "type": ntype,
            "filePath": fpath,
            "summary": get_file_summary(fpath),
            "tags": list(set(tags)),
            "complexity": complexity
        })
        
        # AST symbols (functions/classes)
        file_ast = ast_results.get(fpath)
        if file_ast:
            functions = file_ast.get("functions", [])
            for fn in functions:
                fn_name = fn["name"]
                # Skip double private built-ins unless meaningful
                if fn_name.startswith("__") and fn_name.endswith("__"):
                    continue
                fn_node_id = f"function:{fpath}:{fn_name}"
                fn_lines = fn.get("endLine", 0) - fn.get("startLine", 0)
                fn_comp = "simple"
                if fn_lines > 40:
                    fn_comp = "complex"
                elif fn_lines > 15:
                    fn_comp = "moderate"
                    
                nodes.append({
                    "id": fn_node_id,
                    "name": fn_name,
                    "type": "function",
                    "filePath": fpath,
                    "summary": f"Function `{fn_name}` in {Path(fpath).name}",
                    "tags": list(set(tags + ["function"])),
                    "complexity": fn_comp,
                    "lineRange": [fn.get("startLine", 1), fn.get("endLine", 1)]
                })
                
                # Contains edge
                edges.append({
                    "id": f"edge:{file_node_id}->{fn_node_id}",
                    "source": file_node_id,
                    "target": fn_node_id,
                    "type": "contains",
                    "direction": "forward",
                    "description": f"Contains function {fn_name}"
                })
                
        # Imports edges
        imported_files = batch_import_data.get(fpath, [])
        for imp_file in imported_files:
            imp_type = get_node_type("code", imp_file)
            target_id = f"{imp_type}:{imp_file}"
            edges.append({
                "id": f"edge:{file_node_id}->{target_id}",
                "source": file_node_id,
                "target": target_id,
                "type": "imports",
                "direction": "forward",
                "description": f"Imports {Path(imp_file).name}"
            })

    batch_output_file = intermediate_dir / f"batch-{batch_idx}.json"
    with open(batch_output_file, "w", encoding="utf-8") as f:
        json.dump({
            "batchIndex": batch_idx,
            "nodes": nodes,
            "edges": edges
        }, f, indent=2)
        
    print(f"Batch {batch_idx}: wrote {len(nodes)} nodes, {len(edges)} edges to {batch_output_file.name}")

print("All batches processed.")
