from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, Relationship
from app.models.base import TenantBaseModel

class Category(TenantBaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    
    transactions: List["Transaction"] = Relationship(back_populates="category")

class Account(TenantBaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    balance: float = Field(default=0.0)

    transactions: List["Transaction"] = Relationship(back_populates="account")

class Transaction(TenantBaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    date: datetime
    merchant: str
    status: str = Field(default="Confirmed") # PendingReview, Confirmed, etc.
    
    # On delete behavior in SQLAlchemy/SQLModel (Restrict)
    account_id: int = Field(foreign_key="account.id", ondelete="RESTRICT")
    account: Account = Relationship(back_populates="transactions")
    
    category_id: Optional[int] = Field(default=None, foreign_key="category.id", ondelete="RESTRICT")
    category: Optional[Category] = Relationship(back_populates="transactions")

class BatchIngestion(TenantBaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default="Processing") # Processing, Completed, Failed
    file_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
