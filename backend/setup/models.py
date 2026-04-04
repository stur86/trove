"""Pydantic request/response models for the setup domain."""
from pydantic import BaseModel


class LanguageRequest(BaseModel):
    """Request body for POST /api/setup/language."""
    locale: str


class AdminCredentialsRequest(BaseModel):
    """Request body for POST /api/setup/admin-credentials."""
    username: str
    password: str


class SetupStatus(BaseModel):
    """Response for GET /api/setup/status — which steps are complete."""
    ollama_installed: bool
    models_pulled: list[str]   # list of pulled model tags
    admin_configured: bool     # admin_password is non-empty
    service_installed: bool


class LanUrlResponse(BaseModel):
    """Response for GET /api/setup/lan-url."""
    ip: str
    port: int
    url: str


class OllamaVersionResponse(BaseModel):
    """Response for GET /api/setup/ollama-version."""
    version: str  # e.g. "0.6.2", or "unknown" if not installed


class InstallServiceRequest(BaseModel):
    """Request body for POST /api/setup/install-service."""
    app_port: int = 7770
