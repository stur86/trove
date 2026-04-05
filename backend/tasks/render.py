"""
Jinja2 prompt rendering for Tasks.

Provides render_prompt(), which fills a Task's Jinja2 template with
caller-supplied argument values, merging arg defaults for missing keys.
"""
import jinja2

from backend.tasks.models import Task

_env = jinja2.Environment(undefined=jinja2.StrictUndefined)


def render_prompt(task: Task, values: dict[str, str]) -> str:
    """
    Fill the task's Jinja2 template with argument values.

    Builds a merged dict of {arg.name: arg.default} for all args, then
    overlays the caller-supplied values. Checks that every arg with an
    empty default has a supplied value — raises ValueError if not.

    Args:
        task: The task whose template will be rendered.
        values: Caller-supplied argument values keyed by arg name.

    Returns:
        The rendered prompt string.

    Raises:
        ValueError: If a required arg (empty default, no supplied value) is missing.
        jinja2.TemplateSyntaxError: If the template source is malformed.
        jinja2.UndefinedError: If the template references a variable not in task.args.
    """
    # Check required args before rendering to give a clear error message.
    missing = [
        arg.name
        for arg in task.args
        if arg.default == "" and arg.name not in values
    ]
    if missing:
        raise ValueError(f"Missing required argument(s): {', '.join(missing)}")

    # Merge defaults with supplied values (supplied values take precedence).
    merged = {arg.name: arg.default for arg in task.args}
    merged.update(values)

    template = _env.from_string(task.template)
    return template.render(**merged)
