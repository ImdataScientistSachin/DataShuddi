"""
DataShuddi -- Golden Dataset Fixtures & Benchmark Generator.

Generates 50 labeled ground-truth evaluation samples across 6 domain categories:
Clean, Heavy H/F, Heavy PII, Contextual PII, Schema Fail, and Human Review.

Evaluation record schema (blueprint-mandated):
    test_id, domain, text, ground_truth (pii_locations, hf_lines), failure_taxonomy
"""
from typing import Any

# Failure taxonomy categories
TAXONOMY_PII_LEAK = "PII_LEAK"
TAXONOMY_OVER_REDACTION = "OVER_REDACTION"
TAXONOMY_HF_MISSED = "HF_MISSED"
TAXONOMY_SCHEMA_FAIL = "SCHEMA_FAIL"
TAXONOMY_RETRIEVAL_DROP = "RETRIEVAL_DROP"

# 50 Ground-truth benchmark records
GOLDEN_DATASET: list[dict[str, Any]] = [
    # Category 1: Clean Docs (10 docs)
    *[
        {
            "test_id": f"eval_clean_{i:03d}",
            "domain": "general_reports",
            "text": (
                f"Acme Corporation Quarterly Operations Report #{i}.\n"
                "All regional delivery milestones were achieved within budgeted allocations.\n"
                "Supply chain inventory levels remained stable across all fulfillment hubs throughout the period."
            ),
            "ground_truth": {"pii_locations": [], "hf_lines": []},
            "failure_taxonomy": None,
        }
        for i in range(1, 11)
    ],
    # Category 2: Heavy H/F Docs (10 docs)
    *[
        {
            "test_id": f"eval_hf_{i:03d}",
            "domain": "financial_filings",
            "text": (
                "CONFIDENTIAL | ACME CORP 2024\n"
                f"Financial audit statement page {i}.\n"
                "Operating revenue increased by 14% year-over-year.\n"
                "CONFIDENTIAL | ACME CORP 2024"
            ),
            "ground_truth": {
                "pii_locations": [],
                "hf_lines": ["CONFIDENTIAL | ACME CORP 2024"],
            },
            "failure_taxonomy": TAXONOMY_HF_MISSED,
        }
        for i in range(1, 11)
    ],
    # Category 3: Heavy PII Docs (10 docs)
    *[
        {
            "test_id": f"eval_pii_{i:03d}",
            "domain": "hr_contracts",
            "text": (
                f"Employee Record #{i}: John Smith, SSN: 123-45-{i:04d}, Email: john.smith{i}@acme.com.\n"
                "Employment contract terms verified. Please process onboarding documentation promptly.\n"
                "Contact human resources for any payroll verification inquiries."
            ),
            "ground_truth": {
                "pii_locations": [
                    {"type": "PERSON", "text": "John Smith"},
                    {"type": "US_SSN", "text": f"123-45-{i:04d}"},
                    {"type": "EMAIL_ADDRESS", "text": f"john.smith{i}@acme.com"},
                ],
                "hf_lines": [],
            },
            "failure_taxonomy": TAXONOMY_PII_LEAK,
        }
        for i in range(1, 11)
    ],
    # Category 4: Contextual PII Docs (10 docs)
    *[
        {
            "test_id": f"eval_contextual_{i:03d}",
            "domain": "hr_salary",
            "text": (
                f"Compensation review for Officer #{i}: Base salary $185,000 with executive bonus tier.\n"
                "Performance evaluation rating: Exceeds Expectations across all core leadership competencies.\n"
                "Approved by HR Compensation Committee."
            ),
            "ground_truth": {
                "pii_locations": [{"type": "SALARY", "text": "$185,000"}],
                "hf_lines": [],
            },
            "failure_taxonomy": TAXONOMY_PII_LEAK,
        }
        for i in range(1, 11)
    ],
    # Category 5: Schema Fail Docs (5 docs)
    *[
        {
            "test_id": f"eval_schema_fail_{i:03d}",
            "domain": "corrupted",
            "text": f"Short text #{i}.",
            "ground_truth": {"pii_locations": [], "hf_lines": []},
            "failure_taxonomy": TAXONOMY_SCHEMA_FAIL,
        }
        for i in range(1, 6)
    ],
    # Category 6: Human Review Escalation Docs (5 docs)
    *[
        {
            "test_id": f"eval_human_review_{i:03d}",
            "domain": "edge_cases",
            "text": (
                f"Complex legal agreement #{i} containing multiple conflicting clauses and 60 PII entries.\n"
                + " ".join([f"User_{j}@acme.com" for j in range(1, 61)])
            ),
            "ground_truth": {"pii_locations": [], "hf_lines": []},
            "failure_taxonomy": TAXONOMY_OVER_REDACTION,
        }
        for i in range(1, 6)
    ],
]


def get_golden_dataset() -> list[dict[str, Any]]:
    """Return the 50-doc ground-truth golden dataset."""
    return GOLDEN_DATASET
