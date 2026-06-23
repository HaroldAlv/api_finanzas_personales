from typing import Optional
from sqlmodel import SQLModel, Field

class TenantBaseModel(SQLModel):
    tenant_id: Optional[str] = Field(default=None, index=True, description="Tenant ID for logical isolation")
    is_active: bool = Field(default=True, description="Soft delete flag")
