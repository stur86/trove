"""Task data models for Trove.

A Task is an immutable prompt definition: a Jinja2 template, typed arguments,
capability flags, and output mode. Internal tasks are hardcoded in Python;
user-defined tasks are stored in SQLite.
"""
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class StringArg(BaseModel, frozen=True):
    """A free-text input argument for a task template."""

    type: Literal["string"] = "string"
    name: str
    """Variable name used in the Jinja2 template (e.g. 'topic')."""
    description: str = ""
    """Human-readable hint shown to the user in the UI."""
    default: str = ""
    """Value used when the caller does not supply this argument."""


class ChoiceArg(BaseModel, frozen=True):
    """A fixed-list selection argument for a task template."""

    type: Literal["choice"] = "choice"
    name: str
    """Variable name used in the Jinja2 template."""
    options: list[str]
    """Exhaustive list of allowed values."""
    description: str = ""
    default: str = ""
    """Must be one of options, or empty string for no default."""


TaskArg = Annotated[StringArg | ChoiceArg, Field(discriminator="type")]
"""Discriminated union of all argument types."""


class OutputMode(str, Enum):
    """Expected output format of a task."""

    TEXT = "text"
    STRUCTURED = "structured"  # JSON output — reserved for later


class Task(BaseModel, frozen=True):
    """
    Immutable task definition.

    A task pairs a Jinja2 prompt template with typed arguments. It cannot be
    modified after creation. Use render_prompt() from backend.tasks.render to
    fill in argument values and produce a final prompt string.
    """

    id: str
    """Unique slug identifier (e.g. 'summarise-document')."""
    name: str
    """Human-readable display name."""
    description: str = ""
    """Brief explanation of what this task does."""
    template: str
    """Jinja2 template source. Named args map to {{ variable }} placeholders."""
    args: tuple[TaskArg, ...] = ()
    """Ordered argument definitions. Only StringArg and ChoiceArg appear in templates."""
    has_image: bool = False
    """Task accepts an image input passed alongside the prompt (mock for now)."""
    has_audio: bool = False
    """Task accepts an audio input passed alongside the prompt (mock for now)."""
    output_mode: OutputMode = OutputMode.TEXT
    """Expected output format. STRUCTURED is reserved and not yet implemented."""
