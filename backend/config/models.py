"""Pydantic models for Trove configuration."""
from pydantic import BaseModel, Field


class TroveConfig(BaseModel):
    """
    Persistent configuration for the Trove server.

    Stored as JSON at ~/.config/trove/config.json (XDG-compliant).
    Changes to base_model or num_ctx trigger a Modelfile rebuild.
    """

    base_model: str = "gemma4:e4b"
    """The Ollama base model tag to use (e.g. 'gemma4:e4b', 'gemma4:31b')."""

    num_ctx: int = Field(default=8192, ge=512, le=262144)
    """
    Context window size in tokens passed to Ollama via Modelfile.
    Higher values allow more document content but require more RAM.
    Max depends on the selected model: 131072 for E2B/E4B, 262144 for 26B/31B.
    """

    locale: str = "en"
    """BCP-47 locale code for the UI language (e.g. 'en', 'fr'). Server-wide setting."""

    admin_username: str = "admin"
    """Admin account username used to access the admin panel. Plaintext until full auth system is built."""

    admin_password: str = ""
    """Bcrypt hash of the admin password. Empty string means setup is not complete."""
