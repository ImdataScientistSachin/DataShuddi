"""
DataShuddi -- LangGraph StateGraph Assembly.

Assembles the 8-node StateGraph with all processing nodes, conditional
retry/reflection routing, checkpointer, and memory store.

Graph Topology:
    START
      -> Node 0: security_sanitizer
      -> Node 1: extractor
      -> Node 2: hf_detector
      -> Node 3: pii_detector
      -> Node 4: pii_masker
      -> Node 5: schema_validator
      -> [CONDITIONAL ROUTING]
           validation_passed = True  -> Node 7: output_node -> END
           needs_human_review = True -> END
           validation_passed = False -> Node 6: reflector -> Node 1 (retry)
"""
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from src.agent.checkpoints import get_checkpointer, get_store
from src.agent.nodes.extractor import extractor_node
from src.agent.nodes.hf_detector import hf_detector_node
from src.agent.nodes.output_node import output_node
from src.agent.nodes.pii_detector import pii_detector_node
from src.agent.nodes.pii_masker import pii_masker_node
from src.agent.nodes.reflector import reflector_node
from src.agent.nodes.schema_validator import schema_validator_node
from src.agent.nodes.security_sanitizer import security_sanitizer_node
from src.agent.state import DataShuddiState


def route_after_validation(
    state: DataShuddiState,
) -> Literal["output_node", "reflector", "__end__"]:
    """
    Conditional edge router following Node 5 (Schema Validator).

    Args:
        state: Current DataShuddiState dictionary.

    Returns:
        Next node identifier: "output_node", "reflector", or "__end__".
    """
    if state.get("validation_passed", False):
        return "output_node"
    if state.get("needs_human_review", False):
        return "__end__"
    return "reflector"


def route_after_reflection(
    state: DataShuddiState,
) -> Literal["extractor", "__end__"]:
    """
    Conditional edge router following Node 6 (Reflector).

    Args:
        state: Current DataShuddiState dictionary.

    Returns:
        Next node identifier: "extractor" (retry) or "__end__" (escalated to human review).
    """
    if state.get("needs_human_review", False):
        return "__end__"
    return "extractor"


def build_graph(use_checkpointer: bool = True) -> Any:
    """
    Assemble and compile the DataShuddi 8-node StateGraph.

    Args:
        use_checkpointer: If True, attaches checkpointer for state persistence.

    Returns:
        Compiled LangGraph StateGraph application.
    """
    builder = StateGraph(DataShuddiState)

    # Add all 8 nodes
    builder.add_node("security_sanitizer", security_sanitizer_node)
    builder.add_node("extractor", extractor_node)
    builder.add_node("hf_detector", hf_detector_node)
    builder.add_node("pii_detector", pii_detector_node)
    builder.add_node("pii_masker", pii_masker_node)
    builder.add_node("schema_validator", schema_validator_node)
    builder.add_node("reflector", reflector_node)
    builder.add_node("output_node", output_node)

    # Linear edges from START to Node 5
    builder.add_edge(START, "extractor")
    builder.add_edge("extractor", "security_sanitizer")
    builder.add_edge("security_sanitizer", "hf_detector")
    builder.add_edge("hf_detector", "pii_detector")
    builder.add_edge("pii_detector", "pii_masker")
    builder.add_edge("pii_masker", "schema_validator")

    # Conditional edge after Node 5
    builder.add_conditional_edges(
        "schema_validator",
        route_after_validation,
        {
            "output_node": "output_node",
            "reflector": "reflector",
            END: END,
        },
    )

    # Conditional edge after Node 6 (Reflector retry or human review stop)
    builder.add_conditional_edges(
        "reflector",
        route_after_reflection,
        {
            "extractor": "extractor",
            END: END,
        },
    )

    # Node 7 completes the execution
    builder.add_edge("output_node", END)

    # Checkpointer & Store configuration
    checkpointer = get_checkpointer() if use_checkpointer else None
    store = get_store()

    return builder.compile(checkpointer=checkpointer, store=store)
