"""Pure validation for workflow definitions."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from app.core.exceptions import ValidationAppError

SUPPORTED_STEP_TYPES = {
    "prompt",
    "ai_agent",
    "ai_provider",
    "validation",
    "transformation",
    "storage",
    "conditional",
}


def validate_graph(steps: Iterable[dict]) -> list[dict]:
    """Validate step ids, types, dependencies, and acyclicity."""
    items = list(steps)
    ids = [step.get("key") for step in items]
    if any(not key or not isinstance(key, str) for key in ids):
        raise ValidationAppError("Every workflow step must have a non-empty string key.")
    if len(set(ids)) != len(ids):
        raise ValidationAppError("Workflow step keys must be unique.")

    known = set(ids)
    graph: dict[str, list[str]] = defaultdict(list)
    for step in items:
        step_type = step.get("type")
        if step_type not in SUPPORTED_STEP_TYPES:
            raise ValidationAppError(f"Unsupported workflow step type: {step_type}.")
        dependencies = step.get("depends_on", [])
        if not isinstance(dependencies, list) or any(dep not in known for dep in dependencies):
            raise ValidationAppError(f"Workflow step {step['key']} has an unknown dependency.")
        if step["key"] in dependencies:
            raise ValidationAppError(f"Workflow step {step['key']} cannot depend on itself.")
        graph[step["key"]].extend(dependencies)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in visiting:
            raise ValidationAppError("Workflow graph contains a circular dependency.")
        if key in visited:
            return
        visiting.add(key)
        for dependency in graph[key]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in ids:
        visit(key)
    return items


def topological_order(steps: Iterable[dict]) -> list[dict]:
    items = validate_graph(steps)
    by_key = {step["key"]: step for step in items}
    ordered: list[dict] = []
    remaining = set(by_key)
    while remaining:
        ready = [
            key
            for key in remaining
            if set(by_key[key].get("depends_on", [])) <= {step["key"] for step in ordered}
        ]
        if not ready:
            raise ValidationAppError("Workflow graph cannot be ordered.")
        for key in sorted(ready):
            ordered.append(by_key[key])
            remaining.remove(key)
    return ordered
