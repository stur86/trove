"""Tests for the utility tool catalogue in backend.tasks.tools."""
import pytest
from backend.tasks.models import ToolId
from backend.tasks.tools import build_tool_functions, calculate, get_current_datetime


# ── get_current_datetime ──────────────────────────────────────────────────────

def test_get_current_datetime_returns_string():
    result = get_current_datetime()
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_current_datetime_contains_year():
    result = get_current_datetime()
    import re
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result)


# ── calculate ─────────────────────────────────────────────────────────────────

def test_calculate_addition():
    result = calculate("2 + 2")
    assert "4" in result


def test_calculate_subtraction():
    result = calculate("10 - 3")
    assert "7" in result


def test_calculate_multiplication():
    result = calculate("3 * 4")
    assert "12" in result


def test_calculate_division():
    result = calculate("10 / 2")
    assert "5" in result


def test_calculate_parentheses():
    result = calculate("(3 + 4) * 2")
    assert "14" in result


def test_calculate_exponentiation():
    result = calculate("2^3")
    assert "8" in result


def test_calculate_invalid_expression_returns_error_string():
    result = calculate("not a valid expression @@@@")
    assert "error" in result.lower() or "Error" in result


def test_calculate_returns_string():
    result = calculate("1 + 1")
    assert isinstance(result, str)


# ── build_tool_functions ──────────────────────────────────────────────────────

def test_build_tool_functions_empty_returns_empty_list():
    assert build_tool_functions(frozenset()) == []


def test_build_tool_functions_datetime_returns_one_callable():
    fns = build_tool_functions(frozenset({ToolId.DATETIME}))
    assert len(fns) == 1
    assert callable(fns[0])
    assert fns[0].__name__ == "get_current_datetime"


def test_build_tool_functions_calculator_returns_one_callable():
    fns = build_tool_functions(frozenset({ToolId.CALCULATOR}))
    assert len(fns) == 1
    assert callable(fns[0])
    assert fns[0].__name__ == "calculate"


def test_build_tool_functions_both_returns_two_callables():
    fns = build_tool_functions(frozenset({ToolId.DATETIME, ToolId.CALCULATOR}))
    assert len(fns) == 2
    names = {f.__name__ for f in fns}
    assert names == {"get_current_datetime", "calculate"}


def test_build_tool_functions_order_is_stable():
    """Order follows ToolId enum declaration order regardless of set iteration."""
    fns_a = build_tool_functions(frozenset({ToolId.DATETIME, ToolId.CALCULATOR}))
    fns_b = build_tool_functions(frozenset({ToolId.CALCULATOR, ToolId.DATETIME}))
    assert [f.__name__ for f in fns_a] == [f.__name__ for f in fns_b]
