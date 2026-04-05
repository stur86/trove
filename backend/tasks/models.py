"""Task data models for Trove.

Task is a pure, immutable prompt definition (template + args + capabilities).
UserTask extends Task with the identity and display fields needed for user-facing
Gems stored in the database. Internal tasks use plain Task instances.
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
    """Human-readable hint shown to the user in the UI."""
    default: str = ""
    """Must be one of options, or empty string for no default."""


TaskArg = Annotated[StringArg | ChoiceArg, Field(discriminator="type")]
"""Discriminated union of all argument types."""


class OutputMode(str, Enum):
    """Expected output format of a task."""

    TEXT = "text"
    STRUCTURED = "structured"  # JSON output — reserved for later


class GemHue(str, Enum):
    """
    16 preconfigured display colours for user-facing Gems.

    Named after Tailwind CSS colour palette entries. Used by GemIcon
    in the frontend to select facet colours.
    """

    RED = "red"
    ORANGE = "orange"
    AMBER = "amber"
    YELLOW = "yellow"
    LIME = "lime"
    GREEN = "green"
    EMERALD = "emerald"
    TEAL = "teal"
    CYAN = "cyan"
    SKY = "sky"
    BLUE = "blue"
    INDIGO = "indigo"
    VIOLET = "violet"
    PURPLE = "purple"
    FUCHSIA = "fuchsia"
    ROSE = "rose"


class Task(BaseModel, frozen=True):
    """
    Immutable, pure prompt definition.

    Contains only what is needed to render and execute a prompt:
    a Jinja2 template, typed arguments, multimodal capability flags,
    and the expected output mode. Has no identity or display fields.

    Use render_prompt() from backend.tasks.render to fill in argument
    values and produce a final prompt string.
    """

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


class UserTask(Task, frozen=True):
    """
    A user-defined Task with identity and display metadata.

    Stored in SQLite. Listed by the public Gems API. Rendered in the
    frontend as a Gem card with icon, name, description, and hue.
    """

    id: str
    """Unique slug identifier (e.g. 'summarise-text')."""
    name: str
    """Human-readable title displayed in the UI."""
    description: str = ""
    """Brief explanation of what this Gem does, shown in the card grid."""
    hue: GemHue = GemHue.INDIGO
    """Display colour for the GemIcon. Admin-chosen from 16 preset hues."""
