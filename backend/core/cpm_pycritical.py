from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import networkx as nx
import pandas as pd

from core.models import ALLOWED_REL_TYPES


Dependency: TypeAlias = tuple[str, str, int]
PyCriticalTask: TypeAlias = tuple[str, list[Dependency], int]


@dataclass(frozen=True)
class PyCriticalResult:
    table: pd.DataFrame | None
    cycles_detected: list[list[str]]


def calculate_with_pycritical(dataset: list[PyCriticalTask]) -> PyCriticalResult:
    _validate_dataset(dataset)
    cycles = _detect_cycles(dataset)
    if cycles:
        return PyCriticalResult(table=None, cycles_detected=cycles)

    from pyCritical import critical_path_method_dep

    table = critical_path_method_dep(dataset)
    return PyCriticalResult(table=table, cycles_detected=[])


def _validate_dataset(dataset: list[PyCriticalTask]) -> None:
    task_ids = {task_id for task_id, _, _ in dataset}
    if len(task_ids) != len(dataset):
        raise ValueError("Duplicate task IDs are not allowed")

    for task_id, predecessors, duration in dataset:
        if duration < 0:
            raise ValueError(f"Task {task_id} has a negative duration")
        for pred_id, rel_type, _lag in predecessors:
            if rel_type not in ALLOWED_REL_TYPES:
                raise ValueError(f"Unsupported relationship type for v0.1: {rel_type}")
            if pred_id not in task_ids:
                raise ValueError(f"Task {task_id} references missing predecessor {pred_id}")


def _detect_cycles(dataset: list[PyCriticalTask]) -> list[list[str]]:
    graph = nx.DiGraph()
    for task_id, predecessors, _duration in dataset:
        graph.add_node(task_id)
        for pred_id, _rel_type, _lag in predecessors:
            graph.add_edge(pred_id, task_id)

    try:
        cycle_edges = nx.find_cycle(graph, orientation="original")
    except nx.NetworkXNoCycle:
        return []

    cycle_nodes = [cycle_edges[0][0]]
    cycle_nodes.extend(edge[1] for edge in cycle_edges)
    return [cycle_nodes]
