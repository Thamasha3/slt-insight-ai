from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SystemSettingsOut(BaseModel):
    chat_history_retention_days: int
    admin_chat_enabled: bool
    updated_at: datetime | None = None


class SystemSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat_history_retention_days: int | None = Field(default=None, ge=1, le=3650)
    admin_chat_enabled: bool | None = None
