from pydantic import BaseModel
from typing import Optional


class AccountCreate(BaseModel):
    name: str
    type: str = "bank"


class AccountResponse(BaseModel):
    id: int
    name: str
    type: str

    class Config:
        from_attributes = True
