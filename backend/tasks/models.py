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

AUDIO_CAPABLE_MODELS: frozenset[str] = frozenset({"gemma4:e2b", "gemma4:e4b"})
"""Ollama model tags that support audio input. Only the E2B and E4B Gemma 4 variants."""


def audio_supported(base_model: str) -> bool:
    """Return True if the given Ollama base model tag supports audio input.

    Args:
        base_model: The Ollama tag string (e.g. 'gemma4:e4b').

    Returns:
        True for gemma4:e2b and gemma4:e4b; False for all other tags.
    """
    return base_model in AUDIO_CAPABLE_MODELS


class OutputMode(str, Enum):
    """Expected output format of a task."""

    TEXT = "text"
    STRUCTURED = "structured"  # JSON output — reserved for later


class ToolId(str, Enum):
    """Identifiers for the built-in utility tools available to gem agents."""

    DATETIME = "datetime"
    """Tool that returns the current date and time."""
    CALCULATOR = "calculator"
    """Tool that evaluates a mathematical expression."""


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
    tools: frozenset[ToolId] = frozenset()
    """Set of utility tool IDs enabled for this task. Empty means no tools injected."""


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
    doc_folder_ids: tuple[str, ...] = ()
    """IDs of folders whose entire contents are accessible to this gem."""
    doc_ids: tuple[str, ...] = ()
    """IDs of individually accessible documents (outside of folder grants)."""


class MediaInput(BaseModel, frozen=True):
    """
    Runtime multimodal data attached to a single gem run request.

    Carries optional raw bytes for image and/or audio inputs alongside the
    rendered text prompt. The has_image / has_audio properties let callers
    check presence without inspecting bytes directly.

    image_mime and audio_mime default to the most common browser formats;
    callers should always supply the actual MIME type when the bytes are set.
    """

    image: bytes | None = None
    """Raw image bytes in any browser-supported format (JPEG, PNG, WebP, …)."""
    image_mime: str = "image/jpeg"
    """MIME type of the image bytes (e.g. 'image/jpeg', 'image/png')."""
    audio: bytes | None = None
    """Raw audio bytes — typically audio/webm from the browser MediaRecorder API."""
    audio_mime: str = "audio/webm"
    """MIME type of the audio bytes (e.g. 'audio/webm', 'audio/mp4')."""

    @property
    def has_image(self) -> bool:
        """True when image bytes are present."""
        return self.image is not None

    @property
    def has_audio(self) -> bool:
        """True when audio bytes are present."""
        return self.audio is not None
