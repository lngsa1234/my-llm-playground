"""Deterministic validation for model output and final-goal coverage."""

from __future__ import annotations

import re


def validate_response(response: str) -> dict:
    if not response or not response.strip():
        return {"valid": False, "errors": ["The model returned no visible text."]}
    return {"valid": True, "errors": []}


def validate_final_output(state: dict, response: str) -> dict:
    words = set(re.findall(r"[a-z0-9]{4,}", response.lower()))
    requirements = [entry["text"] for entry in state.get("requirements", [])]
    covered = [item for item in requirements if any(word in words for word in re.findall(r"[a-z0-9]{4,}", item.lower()))]
    missing = [item for item in requirements if item not in covered]
    return {
        "valid": not missing,
        "requirements_total": len(requirements),
        "requirements_covered": len(covered),
        "missing_requirements": missing,
        "note": "Keyword coverage is a transparent heuristic; review the final artifact manually.",
    }
