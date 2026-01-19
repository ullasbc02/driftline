from typing import Dict, List, Set, Tuple

def edge_id(e):
    return (e.get("from"), e.get("to"))

def diff_graphs(baseline_graph: Dict, current_graph: Dict) -> Dict:
    b_edges = baseline_graph.get("edges", []) or []
    c_edges = current_graph.get("edges", []) or []

    b_set: Set[Tuple[str, str]] = set(edge_id(e) for e in b_edges)
    c_set: Set[Tuple[str, str]] = set(edge_id(e) for e in c_edges)

    added = list(c_set - b_set)
    removed = list(b_set - c_set)

    return {
        "added_edges": [{"from": a, "to": b} for a, b in added],
        "removed_edges": [{"from": a, "to": b} for a, b in removed],
    }
