# Utility Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add datetime and calculator tools to Trove gems — admins enable them per-gem via checkboxes; they are injected into the Pydantic AI agent at run time.

**Architecture:** A new `backend/tasks/tools.py` module owns tool callables and a registry. `ToolId` enum and a `tools: frozenset[ToolId]` field are added to `Task`/`UserTask`. `_make_agent()` in `runner.py` merges utility tools with document tools and passes them to `Agent(model, tools=...)`. Pydantic AI reads docstrings and type hints to describe tools to the model — no manual system-prompt construction. The frontend exposes a static checkbox list in `GemForm`.

**Tech Stack:** Python (mathparse for expression parsing), Pydantic AI tool injection, Flowbite React checkboxes, existing SQLite repository pattern.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | Modify | Add `mathparse` production dependency |
| `backend/tasks/models.py` | Modify | Add `ToolId` enum; `tools: frozenset[ToolId]` on `Task` |
| `backend/tasks/tools.py` | **Create** | Tool callables, registry, `build_tool_functions()` |
| `backend/tasks/repository.py` | Modify | Add `tools` column to DDL; serialise/deserialise |
| `backend/tasks/runner.py` | Modify | `_make_agent()` gains `tool_ids` param; callers pass `task.tools` |
| `tests/test_task_models.py` | Modify | Tests for `ToolId` and `Task.tools` field |
| `tests/test_task_tools.py` | **Create** | Tests for tool callables and `build_tool_functions()` |
| `tests/test_task_repository.py` | Modify | Round-trip tests for `tools` column |
| `tests/test_task_runner.py` | Modify | Tests for runner passing tools to `_make_agent()` |
| `frontend/src/api/tasks.ts` | Modify | Add `ToolId` type, `TOOL_IDS` constant, `tools` on `UserTask` |
| `frontend/src/api/mock/tasks.ts` | Modify | Add `tools: []` to all sample tasks |
| `frontend/src/pages/GemForm.tsx` | Modify | Add Tools section with `HelpBar` and checkboxes |
| `locales/en.json` | Modify | Add 9 new locale keys |
| `locales/{de,es,fr,it,pt,zh}.json` | Modify | Translations (dispatched to Haiku agent) |
| `docs/admin/gems.md` | Modify | Add Tools section to admin gem guide |

---

### Task 1: Add mathparse dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add the dependency**

```bash
cd /home/gan_hope326/Projects/trove && uv add mathparse
```

Expected: `pyproject.toml` now lists `mathparse` under `dependencies`; `uv.lock` is updated.

- [ ] **Step 2: Verify import works**

```bash
python -c "import mathparse; print(mathparse.parse('2 + 2'))"
```

Expected: prints `4` or `4.0`.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add mathparse dependency"
```

---

### Task 2: Add ToolId enum and tools field to Task model

**Files:**
- Modify: `backend/tasks/models.py`
- Modify: `tests/test_task_models.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_task_models.py`:

```python
# ── ToolId and Task.tools (utility tools) ────────────────────────────────────

from backend.tasks.models import ToolId  # noqa: E402


def test_tool_id_values():
    assert ToolId.DATETIME.value == "datetime"
    assert ToolId.CALCULATOR.value == "calculator"


def test_tool_id_has_two_members():
    assert len(list(ToolId)) == 2


def test_task_defaults_to_empty_tools():
    task = Task(template="Hello")
    assert task.tools == frozenset()


def test_task_with_single_tool():
    task = Task(template="Hello", tools=frozenset({ToolId.DATETIME}))
    assert ToolId.DATETIME in task.tools
    assert ToolId.CALCULATOR not in task.tools


def test_task_with_multiple_tools():
    task = Task(template="Hello", tools=frozenset({ToolId.DATETIME, ToolId.CALCULATOR}))
    assert ToolId.DATETIME in task.tools
    assert ToolId.CALCULATOR in task.tools


def test_task_is_frozen_with_tools():
    task = Task(template="Hello", tools=frozenset({ToolId.DATETIME}))
    with pytest.raises(ValidationError):
        task.tools = frozenset()  # type: ignore[misc]


def test_user_task_inherits_tools_field():
    task = UserTask(
        id="t1", name="T", template="Hi",
        tools=frozenset({ToolId.CALCULATOR}),
    )
    assert ToolId.CALCULATOR in task.tools
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_task_models.py -k "tool" -v
```

Expected: ImportError or AttributeError — `ToolId` not yet defined.

- [ ] **Step 3: Implement — add ToolId and tools field to models.py**

In `backend/tasks/models.py`, add after the `OutputMode` enum (around line 63):

```python
class ToolId(str, Enum):
    """Identifiers for the built-in utility tools available to gem agents."""

    DATETIME = "datetime"
    """Tool that returns the current date and time."""
    CALCULATOR = "calculator"
    """Tool that evaluates a mathematical expression using mathparse."""
```

In the `Task` class, add `tools` after `output_mode`:

```python
    tools: frozenset[ToolId] = frozenset()
    """Set of utility tool IDs enabled for this task. Empty means no tools injected."""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_task_models.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tasks/models.py tests/test_task_models.py
git commit -m "feat: add ToolId enum and tools field to Task model"
```

---

### Task 3: Create backend/tasks/tools.py

**Files:**
- Create: `backend/tasks/tools.py`
- Create: `tests/test_task_tools.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_task_tools.py`:

```python
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
    assert "2" in result  # year starts with 2 (e.g. 2026)


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_task_tools.py -v
```

Expected: `ModuleNotFoundError` — `backend.tasks.tools` does not exist.

- [ ] **Step 3: Implement backend/tasks/tools.py**

Create `backend/tasks/tools.py`:

```python
"""Utility tool catalogue for Trove gem agents.

Each callable in this module can be passed directly to a Pydantic AI Agent
as a tool. Pydantic AI reads the docstring and type hints to generate the
tool description sent to the model — no separate system prompt construction
is required.
"""
from collections.abc import Callable
from datetime import datetime

import mathparse

from backend.tasks.models import ToolId


def get_current_datetime() -> str:
    """Return the current date and time.

    Call this when the user asks about today's date, the current time,
    or anything requiring knowledge of when the conversation is taking place.
    Returns a human-readable string such as 'Friday, 25 April 2026, 14:32:00'.
    """
    return datetime.now().strftime("%A, %d %B %Y, %H:%M:%S")


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the numeric result.

    Supports arithmetic operators (+, -, *, /), parentheses, exponentiation (**),
    and common constants (e.g. pi). Does not support trigonometric functions.
    Returns an error message string if the expression cannot be evaluated.

    Args:
        expression: A mathematical expression as a string, e.g. '(3 + 4) * 2'.
    """
    try:
        result = mathparse.parse(expression)
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_task_tools.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tasks/tools.py tests/test_task_tools.py
git commit -m "feat: add utility tool catalogue (datetime, calculator)"
```

---

### Task 4: Update repository for tools round-trip

**Files:**
- Modify: `backend/tasks/repository.py`
- Modify: `tests/test_task_repository.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_task_repository.py`:

```python
# ── tools round-trip ──────────────────────────────────────────────────────────

from backend.tasks.models import ToolId  # noqa: E402


def test_tools_default_is_empty_frozenset(data_dir):
    task = UserTask(id="plain", name="Plain", template="Hi")
    save_task(task)
    loaded = load_task("plain")
    assert loaded.tools == frozenset()


def test_tools_single_tool_round_trip(data_dir):
    task = UserTask(
        id="calc-gem", name="Calc", template="Calculate.",
        tools=frozenset({ToolId.CALCULATOR}),
    )
    save_task(task)
    loaded = load_task("calc-gem")
    assert loaded.tools == frozenset({ToolId.CALCULATOR})


def test_tools_multiple_tools_round_trip(data_dir):
    task = UserTask(
        id="both-tools", name="Both", template="Go.",
        tools=frozenset({ToolId.DATETIME, ToolId.CALCULATOR}),
    )
    save_task(task)
    loaded = load_task("both-tools")
    assert loaded.tools == frozenset({ToolId.DATETIME, ToolId.CALCULATOR})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_task_repository.py -k "tools" -v
```

Expected: FAIL — `tools` column missing from DDL; `UserTask` rejects unexpected field or loads wrong value.

- [ ] **Step 3: Implement — update repository.py**

In `_CREATE_TABLE`, add `tools` column (the full DDL string, replacing the existing one):

```python
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    hue             TEXT NOT NULL DEFAULT 'indigo',
    template        TEXT NOT NULL,
    args            TEXT NOT NULL,
    has_image       INTEGER NOT NULL DEFAULT 0,
    has_audio       INTEGER NOT NULL DEFAULT 0,
    output_mode     TEXT NOT NULL DEFAULT 'text',
    doc_folder_ids  TEXT NOT NULL DEFAULT '[]',
    doc_ids         TEXT NOT NULL DEFAULT '[]',
    tools           TEXT NOT NULL DEFAULT '[]'
)
"""
```

In `_row_to_user_task`, add tools deserialisation (add after the `doc_ids` line):

```python
    tools = frozenset(ToolId(t) for t in json.loads(row["tools"] or "[]"))
```

And pass it to `UserTask(...)`:

```python
    return UserTask(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        hue=row["hue"],
        template=row["template"],
        args=args,
        has_image=bool(row["has_image"]),
        has_audio=bool(row["has_audio"]),
        output_mode=row["output_mode"],
        doc_folder_ids=doc_folder_ids,
        doc_ids=doc_ids,
        tools=tools,
    )
```

In `save_task`, add tools serialisation. Add this line after the `doc_ids_json` line:

```python
    tools_json = json.dumps([tid.value for tid in task.tools])
```

Update the INSERT statement to include `tools`:

```python
        conn.execute(
            """INSERT OR REPLACE INTO tasks
               (id, name, description, hue, template, args,
                has_image, has_audio, output_mode, doc_folder_ids, doc_ids, tools)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.id,
                task.name,
                task.description,
                task.hue.value,
                task.template,
                args_json,
                int(task.has_image),
                int(task.has_audio),
                task.output_mode.value,
                doc_folder_ids_json,
                doc_ids_json,
                tools_json,
            ),
        )
```

Also add the import at the top of `repository.py`:

```python
from backend.tasks.models import TaskArg, ToolId, UserTask
```

- [ ] **Step 4: Run full repository test suite**

```bash
pytest tests/test_task_repository.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/tasks/repository.py tests/test_task_repository.py
git commit -m "feat: persist tools field in task repository"
```

---

### Task 5: Update runner to inject utility tools

**Files:**
- Modify: `backend/tasks/runner.py`
- Modify: `tests/test_task_runner.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_task_runner.py`:

```python
# ── Utility tool injection ────────────────────────────────────────────────────

from backend.tasks.models import ToolId  # noqa: E402


@pytest.mark.asyncio
async def test_stream_task_with_datetime_tool_runs():
    """Tools field on task is threaded through — agent runs without error."""
    task = Task(template="What time is it?", tools=frozenset({ToolId.DATETIME}))
    agent = Agent(TestModel(custom_output_text="It is noon."))
    chunks = []
    async for chunk in stream_task(task, {}, _agent=agent):
        chunks.append(chunk)
    assert "It is noon." in "".join(chunks)


@pytest.mark.asyncio
async def test_run_task_with_calculator_tool_returns_response():
    task = Task(template="Calculate 2+2", tools=frozenset({ToolId.CALCULATOR}))
    agent = Agent(TestModel(custom_output_text="4"))
    result = await run_task(task, {}, _agent=agent)
    assert result == "4"


@pytest.mark.asyncio
async def test_stream_task_with_both_tools_runs():
    task = Task(template="Help", tools=frozenset({ToolId.DATETIME, ToolId.CALCULATOR}))
    agent = Agent(TestModel(custom_output_text="Done."))
    chunks = []
    async for chunk in stream_task(task, {}, _agent=agent):
        chunks.append(chunk)
    assert "Done." in "".join(chunks)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_task_runner.py -k "tool" -v
```

Expected: FAIL — `Task` has no `tools` attribute in the runner's eyes yet (import mismatch), or the test just confirms current behaviour.

Actually these tests use `_agent=agent` so they bypass `_make_agent`. They will likely pass immediately since `Task` already has the field from Task 2. Run them anyway to confirm they pass — if they do, proceed to implement `_make_agent` changes and write an integration-style test for `_make_agent` directly.

- [ ] **Step 3: Add a direct _make_agent test**

Append to `tests/test_task_runner.py`:

```python
from backend.tasks.runner import _make_agent  # noqa: E402


def test_make_agent_with_no_args_returns_plain_agent():
    agent = _make_agent()
    # Agent is constructed without tools — just verify it is an Agent instance
    from pydantic_ai import Agent as PAAgent
    assert isinstance(agent, PAAgent)


def test_make_agent_with_tool_ids_includes_utility_tools():
    from backend.tasks.models import ToolId
    agent = _make_agent(tool_ids=frozenset({ToolId.DATETIME, ToolId.CALCULATOR}))
    from pydantic_ai import Agent as PAAgent
    assert isinstance(agent, PAAgent)
    # Verify tools were registered — Pydantic AI stores them in _function_tools
    tool_names = {name for name in agent._function_tools}
    assert "get_current_datetime" in tool_names
    assert "calculate" in tool_names
```

- [ ] **Step 4: Run new _make_agent tests to verify they fail**

```bash
pytest tests/test_task_runner.py -k "make_agent" -v
```

Expected: FAIL — `_make_agent` does not accept `tool_ids` yet.

- [ ] **Step 5: Implement — update runner.py**

Add import at the top of `backend/tasks/runner.py`:

```python
from backend.tasks.models import MediaInput, Task, ToolId
from backend.tasks.tools import build_tool_functions
```

Replace `_make_agent` with:

```python
def _make_agent(
    documents: list[Document] | None = None,
    tool_ids: frozenset[ToolId] | None = None,
) -> Agent:
    """Create a Pydantic AI Agent backed by the local trove_model Ollama model.

    When documents are provided, document-access tools and a guiding system
    prompt are added. When tool_ids are provided, utility tool callables are
    added — Pydantic AI derives their descriptions from docstrings and type
    hints automatically.

    Args:
        documents: Documents in scope for this run. None or empty → no document tools.
        tool_ids: Utility tool IDs to inject. None or empty → no utility tools.
    """
    model = OpenAIChatModel(
        "trove_model",
        provider=OllamaProvider(base_url=_OLLAMA_BASE_URL),
    )
    tools: list = []
    system_prompt: str | None = None

    if documents:
        tools.extend(_build_document_tools(documents))
        system_prompt = _DOC_SYSTEM_PROMPT

    if tool_ids:
        tools.extend(build_tool_functions(tool_ids))

    if not tools:
        return Agent(model)
    return Agent(model, tools=tools, system_prompt=system_prompt)
```

In `stream_task`, change the `_make_agent` call:

```python
    agent = _agent or _make_agent(documents, task.tools if task.tools else None)
```

In `run_task`, change the `_make_agent` call:

```python
    agent = _agent or _make_agent(documents, task.tools if task.tools else None)
```

- [ ] **Step 6: Run full runner test suite**

```bash
pytest tests/test_task_runner.py -v
```

Expected: all pass.

- [ ] **Step 7: Run full test suite**

```bash
pytest -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add backend/tasks/runner.py tests/test_task_runner.py
git commit -m "feat: inject utility tools into gem agent via _make_agent"
```

---

### Task 6: Update frontend types

**Files:**
- Modify: `frontend/src/api/tasks.ts`
- Modify: `frontend/src/api/mock/tasks.ts`

- [ ] **Step 1: Add ToolId type and TOOL_IDS constant to tasks.ts**

In `frontend/src/api/tasks.ts`, add after the `GEM_HUES` constant (after line 24):

```typescript
/** The two built-in utility tool identifiers. */
export type ToolId = 'datetime' | 'calculator'

/**
 * Static catalogue of available tools.
 * Keys reference locale strings for labels and descriptions.
 * Update this list when new tools are added to the backend.
 */
export const TOOL_IDS: { id: ToolId; labelKey: string; descKey: string }[] = [
  {
    id: 'datetime',
    labelKey: 'gem.tools.datetime',
    descKey: 'gem.tools.datetime.description',
  },
  {
    id: 'calculator',
    labelKey: 'gem.tools.calculator',
    descKey: 'gem.tools.calculator.description',
  },
]
```

In the `UserTask` interface, add `tools` after `doc_ids`:

```typescript
  /** IDs of built-in utility tools enabled for this gem. */
  tools: ToolId[]
```

- [ ] **Step 2: Update mock tasks to include tools field**

In `frontend/src/api/mock/tasks.ts`, add `tools: []` to every object in `SAMPLE_TASKS` — each gem object should gain this line after `doc_ids: []`:

```typescript
    tools: [],
```

(Repeat for all 5 sample tasks: summarise-text, translate, draft-letter, explain-simply, meeting-notes.)

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /home/gan_hope326/Projects/trove/frontend && bun run build 2>&1 | tail -20
```

Expected: build succeeds with no type errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/tasks.ts frontend/src/api/mock/tasks.ts
git commit -m "feat: add ToolId type and tools field to frontend UserTask"
```

---

### Task 7: Add Tools section to GemForm

**Files:**
- Modify: `frontend/src/pages/GemForm.tsx`

- [ ] **Step 1: Update blankGem and add TOOL_IDS import**

In `GemForm.tsx`, update the import from `../api/tasks`:

```typescript
import {
  gemsApi, GEM_HUES, TOOL_IDS, type TaskArg, type ToolId, type UserTask,
} from '../api/tasks'
```

In `blankGem()`, add `tools: []` after `doc_ids: []`:

```typescript
function blankGem(): UserTask {
  return {
    id: '',
    name: '',
    description: '',
    hue: 'indigo',
    template: '',
    args: [],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
    doc_folder_ids: [],
    doc_ids: [],
    tools: [],
  }
}
```

- [ ] **Step 2: Add Tools section to the form JSX**

In the JSX return, add the following block after the closing `</div>` of the "Capability flags" section (the block containing the image checkbox, around line 418 in the original file):

```tsx
        {/* Tools */}
        <div className="flex flex-col gap-2">
          <Label>{t('gem.tools.section_title')}</Label>
          <HelpBar
            prompt={t('help.gem.tools.prompt')}
            title={t('help.gem.tools.title')}
            content={t('help.gem.tools.content')}
          />
          <p className="text-xs text-gray-500">{t('gem.tools.section_hint')}</p>
          <div className="flex flex-col gap-2">
            {TOOL_IDS.map(({ id, labelKey, descKey }) => (
              <div key={id} className="flex items-start gap-2">
                <Checkbox
                  id={`tool-${id}`}
                  checked={gem.tools.includes(id)}
                  onChange={e => setGem(g => ({
                    ...g,
                    tools: e.target.checked
                      ? [...g.tools, id]
                      : g.tools.filter(tid => tid !== id),
                  }))}
                />
                <div>
                  <Label htmlFor={`tool-${id}`}>{t(labelKey)}</Label>
                  <p className="text-xs text-gray-400 mt-0.5">{t(descKey)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /home/gan_hope326/Projects/trove/frontend && bun run build 2>&1 | tail -20
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/GemForm.tsx
git commit -m "feat: add Tools section to GemForm with HelpBar and checkboxes"
```

---

### Task 8: Locale keys and translations

**Files:**
- Modify: `locales/en.json`
- Modify: `locales/de.json`, `locales/es.json`, `locales/fr.json`, `locales/it.json`, `locales/pt.json`, `locales/zh.json`

- [ ] **Step 1: Add English locale keys**

In `locales/en.json`, append these 9 keys before the final `}` (after the existing `help.gem.documents.*` keys):

```json
  "gem.tools.section_title": "Tools",
  "gem.tools.section_hint": "Allow the model to call these built-in tools during a run.",
  "gem.tools.datetime": "Date & time",
  "gem.tools.datetime.description": "Lets the model look up the current date and time.",
  "gem.tools.calculator": "Calculator",
  "gem.tools.calculator.description": "Lets the model evaluate a mathematical expression.",
  "help.gem.tools.prompt": "What are tools?",
  "help.gem.tools.title": "Tools",
  "help.gem.tools.content": "Tools let the model perform actions during a run — like checking the current date or doing a calculation — before writing its answer. Only enable tools that are relevant to what this gem does."
```

- [ ] **Step 2: Dispatch Haiku agent to translate to all other locales**

Dispatch a `claude-haiku-4-5-20251001` agent with the following task:

> Add translations for 9 new locale keys to each of these files: `locales/de.json`, `locales/es.json`, `locales/fr.json`, `locales/it.json`, `locales/pt.json`, `locales/zh.json`. For each file, read its contents, append the translated versions of the following keys (maintaining the same JSON structure and indentation as the rest of the file), and write it back.
>
> The English source values are:
> - `"gem.tools.section_title"`: `"Tools"`
> - `"gem.tools.section_hint"`: `"Allow the model to call these built-in tools during a run."`
> - `"gem.tools.datetime"`: `"Date & time"`
> - `"gem.tools.datetime.description"`: `"Lets the model look up the current date and time."`
> - `"gem.tools.calculator"`: `"Calculator"`
> - `"gem.tools.calculator.description"`: `"Lets the model evaluate a mathematical expression."`
> - `"help.gem.tools.prompt"`: `"What are tools?"`
> - `"help.gem.tools.title"`: `"Tools"`
> - `"help.gem.tools.content"`: `"Tools let the model perform actions during a run — like checking the current date or doing a calculation — before writing its answer. Only enable tools that are relevant to what this gem does."`
>
> Translate each value into the language of the target file (de=German, es=Spanish, fr=French, it=Italian, pt=Portuguese, zh=Simplified Chinese). Keep the JSON keys in English exactly as written above.

- [ ] **Step 3: Verify all locale files are valid JSON**

```bash
for f in locales/*.json; do python3 -c "import json; json.load(open('$f'))" && echo "$f OK"; done
```

Expected: each file prints `OK`.

- [ ] **Step 4: Commit**

```bash
git add locales/
git commit -m "feat: add utility tools locale keys (en + 6 translations)"
```

---

### Task 9: Update admin docs

**Files:**
- Modify: `docs/admin/gems.md`

- [ ] **Step 1: Add Tools section to the gem admin guide**

In `docs/admin/gems.md`, add a new section between "Document access" and "Editing and deleting":

```markdown
## Tools

Each gem can be given access to built-in tools that the AI can call during a run — for example, to look up the current time or evaluate a calculation — before writing its answer.

| Tool | What it does |
|---|---|
| **Date & time** | Returns the current date and time. Enable this if users may ask questions like "What day is today?" or if the output depends on the current date. |
| **Calculator** | Evaluates a mathematical expression (arithmetic, parentheses, powers). Enable this for gems that involve numeric reasoning or calculations. |

Tools consume a small amount of context window space on every run. Only enable the tools that are genuinely relevant to what the gem does.

!!! note "No trigonometric functions"
    The calculator tool does not support trigonometric functions (sin, cos, tan). Standard arithmetic, parentheses, and exponentiation are fully supported.
```

Also update the **Creating a gem** field table to add a Tools row:

In the table under `## Creating a gem`, add after the `| **Document access** | ... |` row:

```markdown
| **Tools** | Optional built-in capabilities the AI can call during a run (date/time, calculator). |
```

- [ ] **Step 2: Commit**

```bash
git add docs/admin/gems.md
git commit -m "docs: add Tools section to admin gem guide"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| `ToolId` enum in `models.py` | Task 2 |
| `tools: frozenset[ToolId]` on `Task` | Task 2 |
| `backend/tasks/tools.py` with `get_current_datetime`, `calculate`, `build_tool_functions`, registry | Task 3 |
| `mathparse` dependency | Task 1 |
| `_make_agent()` merges utility + document tools | Task 5 |
| `stream_task`/`run_task` pass `task.tools` | Task 5 |
| Repository `tools` column, serialise/deserialise | Task 4 |
| `ToolId` type + `TOOL_IDS` constant in `tasks.ts` | Task 6 |
| `tools: ToolId[]` on `UserTask` | Task 6 |
| `blankGem()` initialises `tools: []` | Task 7 |
| Tools section in GemForm with HelpBar + checkboxes | Task 7 |
| English locale keys | Task 8 |
| Translations to de/es/fr/it/pt/zh | Task 8 |
| Docs — admin gem guide | Task 9 |

All spec requirements are covered.
