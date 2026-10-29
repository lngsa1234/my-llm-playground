"""A ToolRegistry: the same shape as week4_tools, assembled from enabled connectors.

`ToolRegistry.execute` is a drop-in for `week4_tools.execute`, and `schemas_for` for
`week4_tools.schemas`, so the agent takes a registry as an *optional* parameter. When
no registry is passed the agent behaves exactly as before (keeping tests and Week 6
deterministic); when one is passed, live connectors do the real work.

`build_registry` always includes every connector (so the full Mini Muse tool set stays
available) plus the offline built-ins `calculator` and `search_notes`. A connector that
the user has not switched to Live runs in simulated mode, so an all-simulated registry
is behaviorally identical to the default fake world.
"""

from __future__ import annotations

from typing import Callable

from mini_muse import week4_tools

# Offline tools that never touch a connector: pure-Python calculator and notes RAG.
BUILTIN_TOOLS = ["calculator", "search_notes"]


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
    """Merge every connector's tools (live where the user opted in, else simulated).

    selections: {connector_name: {"enabled": bool, "mode": "simulated"|"live", "creds": {...}}}
    """
    schemas: dict[str, dict] = {}
    functions: dict[str, Callable] = {}
    risky: set[str] = set()
    names: list[str] = []

    for conn in connectors:
        sel = selections.get(conn.name) or {}
        want_live = bool(sel.get("enabled")) and sel.get("mode") == "live"
        creds = sel.get("creds", {}) if want_live else {}
        # Fall back to simulated when live is requested but not ready (missing creds / not
        # connected). The UI already shows why; a live call would only return an error.
        live = want_live and conn.readiness("live", creds).ready
        mode = "live" if live else "simulated"
        for schema in conn.schemas():
            fname = schema["function"]["name"]
            schemas[fname] = schema
            if fname not in names:
                names.append(fname)
        functions.update(conn.functions(mode, creds, world=world))
        risky |= conn.risky_tools(mode)

    for name in BUILTIN_TOOLS:
        schemas[name] = week4_tools.SCHEMAS[name]
        functions[name] = week4_tools.FUNCTIONS[name]
        if name not in names:
            names.append(name)

    return ToolRegistry(schemas, functions, risky, names)
