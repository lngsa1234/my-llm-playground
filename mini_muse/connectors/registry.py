"""A ToolRegistry: the same shape as week4_tools, assembled from live connectors.

`ToolRegistry.execute` is a drop-in for `week4_tools.execute`, and `schemas_for` for
`week4_tools.schemas`, so the agent takes a registry as an *optional* parameter. When
no registry is passed the agent behaves exactly as before (keeping tests and Week 6
deterministic); when one is passed, live connectors do the real work.

`build_registry` includes only enabled, connected live connectors plus the offline
built-in `calculator`. There is no simulated fallback.
"""

from __future__ import annotations

from typing import Callable

from mini_muse import week4_tools

# Offline tool that never touches a connector: pure-Python calculator.
# Notes are supplied in the dedicated Week 3 exercise, not silently loaded from samples.
BUILTIN_TOOLS = ["calculator"]


class ToolRegistry:
    """Name-keyed tools, mirroring week4_tools' globals for one set of connector choices."""

    def __init__(self, schemas: dict[str, dict], functions: dict[str, Callable],
                 risky: set[str], names: list[str]):
        self._schemas = schemas          # tool name -> schema dict
        self.functions = functions       # tool name -> fn(world, **args) -> dict
        self.risky = set(risky)          # tools that need approval in this configuration
        self.names = names               # available tool names, in order

    def schemas_for(self, names) -> list[dict]:
        """Schemas for the requested names that this registry actually has."""
        return [self._schemas[n] for n in names if n in self._schemas]

    def execute(self, world: dict, name: str, args: dict, **extra) -> dict:
        """Run one tool. Drop-in for week4_tools.execute: errors become results, never crashes."""
        fn = self.functions.get(name)
        if fn is None:
            return {"error": f"Unknown tool {name!r}."}
        try:
            if name == "search_notes":
                return fn(world, **args, **extra)
            return fn(world, **args)
        except TypeError as exc:
            return {"error": f"Bad arguments for {name}: {exc}"}


def build_registry(connectors, selections: dict, *, world: dict) -> ToolRegistry:
    """Merge enabled, ready live connectors; unavailable connectors are omitted."""
    schemas: dict[str, dict] = {}
    functions: dict[str, Callable] = {}
    risky: set[str] = set()
    names: list[str] = []

    for conn in connectors:
        sel = selections.get(conn.name) or {}
        if not sel.get("enabled"):
            continue
        creds = sel.get("creds", {})
        if not conn.readiness("live", creds).ready:
            continue
        for schema in conn.schemas():
            fname = schema["function"]["name"]
            schemas[fname] = schema
            if fname not in names:
                names.append(fname)
        functions.update(conn.functions("live", creds, world=world))
        risky |= conn.risky_tools("live")

    for name in BUILTIN_TOOLS:
        schemas[name] = week4_tools.SCHEMAS[name]
        functions[name] = week4_tools.FUNCTIONS[name]
        if name not in names:
            names.append(name)

    return ToolRegistry(schemas, functions, risky, names)
