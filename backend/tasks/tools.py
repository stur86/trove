"""Utility tool catalogue for Trove gem agents.

Each callable in this module can be passed directly to a Pydantic AI Agent
as a tool. Pydantic AI reads the docstring and type hints to generate the
tool description sent to the model — no separate system prompt construction
is required.
"""
from collections.abc import Callable
from datetime import datetime

from mathparse import mathparse as _mathparse

from backend.tasks.models import ToolId


def get_current_datetime() -> str:
    """Return the current date and time in ISO format.

    Call this when the user asks about today's date, the current time,
    or anything requiring knowledge of when the conversation is taking place.
    Returns a string in the format 'YYYY-MM-DD HH:MM:SS', e.g. '2026-04-25 14:32:00'.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the numeric result.

    Supports arithmetic operators (+, -, *, /), parentheses, exponentiation (^, e.g. 2^3),
    and common constants (e.g. pi). Does not support trigonometric functions.
    Returns an error message string if the expression cannot be evaluated.

    Args:
        expression: A mathematical expression as a string, e.g. '(3 + 4) * 2'.
    """
    try:
        result = _mathparse.parse(expression)
        return str(result)
    except Exception as exc:
        return f"Error: could not evaluate '{expression}': {exc}"


_TOOL_REGISTRY: dict[ToolId, Callable] = {
    ToolId.DATETIME: get_current_datetime,
    ToolId.CALCULATOR: calculate,
}


def build_tool_functions(tool_ids: frozenset[ToolId]) -> list[Callable]:
    """Return the callable tools for the requested tool IDs.

    Iterates ToolId in enum declaration order to produce a stable list
    regardless of set iteration order.

    Args:
        tool_ids: Set of ToolId values to include.

    Returns:
        List of callables in ToolId enum order. Empty list if tool_ids is empty.
    """
    return [_TOOL_REGISTRY[tid] for tid in ToolId if tid in tool_ids]
