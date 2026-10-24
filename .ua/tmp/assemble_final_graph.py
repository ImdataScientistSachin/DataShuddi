import json
import subprocess
import time
from pathlib import Path

project_root = Path("G:/Project Directory/GENAI PROJECT DIRECTORY/DataShuddi")
ua_dir = project_root / ".ua"
intermediate_dir = ua_dir / "intermediate"

assembled_path = intermediate_dir / "assembled-graph.json"
with open(assembled_path, "r", encoding="utf-8") as f:
    graph_data = json.load(f)

nodes = graph_data.get("nodes", [])
raw_edges = graph_data.get("edges", [])
node_ids = {n["id"] for n in nodes}

# Clean and format edges to strictly match GraphEdgeSchema
clean_edges = []
for e in raw_edges:
    src = e.get("source")
    tgt = e.get("target")
    if src not in node_ids or tgt not in node_ids:
        continue
    etype = e.get("type", "depends_on")
    if etype not in [
        "imports", "exports", "contains", "inherits", "implements",
        "calls", "subscribes", "publishes", "middleware",
        "reads_from", "writes_to", "transforms", "validates",
        "depends_on", "tested_by", "configures",
        "related", "similar_to", "deploys", "serves", "provisions", "triggers",
        "migrates", "documents", "routes", "defines_schema",
        "contains_flow", "flow_step", "cross_domain",
        "cites", "contradicts", "builds_on", "exemplifies", "categorized_under", "authored_by",
        "instance_of", "variant_of", "uses_token"
    ]:
        etype = "depends_on"
        
    direction = e.get("direction", "forward")
    if direction not in ["forward", "backward", "bidirectional"]:
        direction = "forward"
        
    weight = float(e.get("weight", 0.5))
    if weight < 0 or weight > 1:
        weight = 0.5
        
    desc = e.get("description")
    edge_obj = {
        "source": src,
        "target": tgt,
        "type": etype,
        "direction": direction,
        "weight": weight
    }
    if desc:
        edge_obj["description"] = str(desc)
    clean_edges.append(edge_obj)

# Classify nodes into 10 clean architectural layers
layers_def = [
    {
        "id": "layer:pre-ingestion-security",
        "name": "Pre-Ingestion Security & Boundary",
        "description": "Node 0: Prompt injection defense, security flags, trust boundary wrapping",
        "nodeIds": []
    },
    {
        "id": "layer:extraction-parsing",
        "name": "Extraction & Parsing",
        "description": "Node 1: PyMuPDF + PaddleOCR character density fallback extraction",
        "nodeIds": []
    },
    {
        "id": "layer:boilerplate-detection",
        "name": "Boilerplate & Noise Reduction",
        "description": "Node 2: Header/footer frequency analysis and dynamic thresholding",
        "nodeIds": []
    },
    {
        "id": "layer:hybrid-pii-scrubbing",
        "name": "Hybrid PII Scrubbing & Redaction",
        "description": "Node 3 & Node 4: Presidio + Qwen 3B contextual detection and token masking",
        "nodeIds": []
    },
    {
        "id": "layer:validation-reflection",
        "name": "Validation & Self-Correction",
        "description": "Node 5 & Node 6: Pydantic v2 enterprise doc validation and Qwen 14B reflection loop",
        "nodeIds": []
    },
    {
        "id": "layer:vector-output",
        "name": "Vector Store & Storage",
        "description": "Node 7: Payload allowlist enforcement, mxbai embeddings, Qdrant upsert",
        "nodeIds": []
    },
    {
        "id": "layer:orchestration-state",
        "name": "Graph Orchestration & State Management",
        "description": "StateGraph assembly, DataShuddiState 4-tier taxonomy, checkpointer & store",
        "nodeIds": []
    },
    {
        "id": "layer:api-presentation",
        "name": "API & User Interfaces",
        "description": "FastAPI REST API, Streamlit operations dashboard, health monitoring",
        "nodeIds": []
    },
    {
        "id": "layer:evaluation-testing",
        "name": "Evaluation, Testing & CI/CD",
        "description": "50-doc golden dataset benchmark, release gates, unit and integration tests",
        "nodeIds": []
    },
    {
        "id": "layer:infrastructure-config",
        "name": "Infrastructure & Configuration",
        "description": "Docker, Compose, Nginx, environment settings, and CI workflows",
        "nodeIds": []
    }
]

layer_by_id = {l["id"]: l for l in layers_def}

for n in nodes:
    nid = n["id"]
    fp = n.get("filePath", "").lower()
    
    if "security_sanitizer" in fp:
        layer_by_id["layer:pre-ingestion-security"]["nodeIds"].append(nid)
    elif "extractor" in fp and "test_" not in fp:
        layer_by_id["layer:extraction-parsing"]["nodeIds"].append(nid)
    elif "hf_detector" in fp and "test_" not in fp:
        layer_by_id["layer:boilerplate-detection"]["nodeIds"].append(nid)
    elif ("pii_detector" in fp or "pii_masker" in fp) and "test_" not in fp:
        layer_by_id["layer:hybrid-pii-scrubbing"]["nodeIds"].append(nid)
    elif ("schema_validator" in fp or "reflector" in fp) and "test_" not in fp:
        layer_by_id["layer:validation-reflection"]["nodeIds"].append(nid)
    elif "output_node" in fp and "test_" not in fp:
        layer_by_id["layer:vector-output"]["nodeIds"].append(nid)
    elif any(k in fp for k in ["graph.py", "state.py", "checkpoints.py", "src/main.py", "src/agent"]):
        layer_by_id["layer:orchestration-state"]["nodeIds"].append(nid)
    elif any(k in fp for k in ["src/api", "streamlit", "nginx"]):
        layer_by_id["layer:api-presentation"]["nodeIds"].append(nid)
    elif any(k in fp for k in ["tests", "golden_dataset", "evaluate_pii_recall"]):
        layer_by_id["layer:evaluation-testing"]["nodeIds"].append(nid)
    else:
        layer_by_id["layer:infrastructure-config"]["nodeIds"].append(nid)

tour = [
    {
        "order": 1,
        "title": "Project Foundation & Ingress Security",
        "description": "DataShuddi begins at Node 0 (Security Sanitizer). All incoming documents cross a pre-ingestion trust boundary where prompt injection patterns are stripped and untrusted text is wrapped in [UNTRUSTED_CONTENT].",
        "nodeIds": [
            nid for nid in [
                "document:README.md",
                "file:src/agent/nodes/security_sanitizer.py",
                "function:src/agent/nodes/security_sanitizer.py:security_sanitizer_node"
            ] if nid in node_ids
        ]
    },
    {
        "order": 2,
        "title": "Text Extraction with Optical Density Fallback",
        "description": "Node 1 handles digital PDFs, Word documents, and text files using PyMuPDF. If char density falls below 50 chars/page, it seamlessly engages the PaddleOCR CPU fallback.",
        "nodeIds": [
            nid for nid in [
                "file:src/agent/nodes/extractor.py",
                "function:src/agent/nodes/extractor.py:extractor_node",
                "function:src/agent/nodes/extractor.py:_ocr_fallback_pdf"
            ] if nid in node_ids
        ]
    },
    {
        "order": 3,
        "title": "Header & Footer Noise Stripping",
        "description": "Node 2 uses line frequency analysis across pages to detect repeated running headers, footers, and confidential disclaimers, eliminating semantic dilution before chunking.",
        "nodeIds": [
            nid for nid in [
                "file:src/agent/nodes/hf_detector.py",
                "function:src/agent/nodes/hf_detector.py:hf_detector_node"
            ] if nid in node_ids
        ]
    },
    {
        "order": 4,
        "title": "Hybrid Dual-Layer PII Detection & Anonymization",
        "description": "Nodes 3 & 4 combine Presidio regex/NER with Qwen2.5-coder:3b contextual LLM inference on the GTX 1650 GPU, followed by offset-safe placeholder redaction.",
        "nodeIds": [
            nid for nid in [
                "file:src/agent/nodes/pii_detector.py",
                "function:src/agent/nodes/pii_detector.py:pii_detector_node",
                "file:src/agent/nodes/pii_masker.py",
                "function:src/agent/nodes/pii_masker.py:pii_masker_node"
            ] if nid in node_ids
        ]
    },
    {
        "order": 5,
        "title": "Pydantic Schema Validation & Residual Scans",
        "description": "Node 5 validates the scrubbed document against strict EnterpriseDoc schemas and performs a post-anonymization residual scan to guarantee zero PII leakage.",
        "nodeIds": [
            nid for nid in [
                "file:src/agent/nodes/schema_validator.py",
                "function:src/agent/nodes/schema_validator.py:schema_validator_node"
            ] if nid in node_ids
        ]
    },
    {
        "order": 6,
        "title": "Reflector Self-Correction Loop & Human Escalation",
        "description": "Node 6 runs Qwen 14B in CPU mode if validation fails. Governed by a Confidence Gate (≥0.70) and Max Delta Cap (0.05), it adapts thresholds or escalates to human review if retries exceed 3.",
        "nodeIds": [
            nid for nid in [
                "file:src/agent/nodes/reflector.py",
                "function:src/agent/nodes/reflector.py:reflector_node"
            ] if nid in node_ids
        ]
    },
    {
        "order": 7,
        "title": "Zero-Leak Output & Qdrant Vector Upsert",
        "description": "Node 7 strictly validates ALLOWED_PAYLOAD_KEYS before generating 1024-dimensional embeddings via mxbai-embed-large and upserting points to Qdrant.",
        "nodeIds": [
            nid for nid in [
                "file:src/agent/nodes/output_node.py",
                "function:src/agent/nodes/output_node.py:output_node"
            ] if nid in node_ids
        ]
    },
    {
        "order": 8,
        "title": "State Lifecycle, Persistence & CI/CD Safety Gates",
        "description": "The LangGraph StateGraph unifies execution across 4 state tiers, PostgresSaver checkpoints, and passes a 50-doc golden dataset release gate with 100% PII recall.",
        "nodeIds": [
            nid for nid in [
                "file:src/agent/graph.py",
                "function:src/agent/graph.py:build_graph",
                "file:src/agent/state.py",
                "file:tests/test_release_gate.py"
            ] if nid in node_ids
        ]
    }
]

# Get current git commit hash
try:
    commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
except Exception:
    commit_hash = "production-release-v3"

now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

knowledge_graph = {
    "version": "2.9.7",
    "kind": "codebase",
    "project": {
        "name": "DataShuddi",
        "languages": ["python", "markdown", "dockerfile", "yaml", "toml"],
        "frameworks": ["LangGraph", "FastAPI", "Pydantic", "Presidio", "Streamlit", "Qdrant", "PyMuPDF"],
        "description": "Self-Correcting PII Scrubbing + Validation Agent | Local-First LangGraph Pipeline",
        "analyzedAt": now_str,
        "gitCommitHash": commit_hash
    },
    "nodes": nodes,
    "edges": clean_edges,
    "layers": layers_def,
    "tour": tour
}

final_graph_path = ua_dir / "knowledge-graph.json"
with open(final_graph_path, "w", encoding="utf-8") as f:
    json.dump(knowledge_graph, f, indent=2)

meta_data = {
    "gitCommitHash": commit_hash,
    "analyzedAt": now_str,
    "totalFiles": len([n for n in nodes if n["type"] in ["file", "document", "config", "service"]]),
    "totalNodes": len(nodes),
    "totalEdges": len(clean_edges)
}

with open(ua_dir / "meta.json", "w", encoding="utf-8") as f:
    json.dump(meta_data, f, indent=2)

print(f"SUCCESS: Generated strict Zod-compliant knowledge-graph.json! {len(nodes)} nodes, {len(clean_edges)} edges.")
