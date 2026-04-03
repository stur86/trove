from pydantic import BaseModel, Field


class TroveConfig(BaseModel):
    base_model: str = "gemma4:e4b"
    num_ctx: int = Field(default=8192, ge=512, le=262144)
    locale: str = "en"
