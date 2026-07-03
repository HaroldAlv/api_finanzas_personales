from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from app.models.base import TenantBaseModel


# ── Global tables (no tenant_id, no is_active) ──────────────────────────

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None, description="Category context for AI")

    transactions: List["Transaction"] = Relationship(back_populates="category")


class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: str = Field(default="bank", description="bank, digital_wallet, cash, merchant")

    transactions_from: List["Transaction"] = Relationship(
        back_populates="account_from",
        sa_relationship_kwargs={"foreign_keys": "Transaction.id_from_account"},
    )
    transactions_destination: List["Transaction"] = Relationship(
        back_populates="account_destination",
        sa_relationship_kwargs={"foreign_keys": "Transaction.id_destination_account"},
    )


# ── Tenant-scoped tables ────────────────────────────────────────────────

class BatchIngestion(TenantBaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default="Processing")  # Processing, Completed, Failed
    file_count: int = Field(default=0)
    total_processed: int = Field(default=0)
    total_failed: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)

    transactions: List["Transaction"] = Relationship(back_populates="batch")


class Transaction(TenantBaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    date: datetime
    description: str                                            # Required (primary field)
    transaction_type: str = Field(default="expense")            # expense, income, transfer
    name_from: str                                              # Who sends (text)
    name_destination: str                                       # Who receives (text)
    source: str = Field(default="manual")                       # manual, smart_ingestion, bulk
    original_file_path: Optional[str] = Field(default=None)
    status: str = Field(default="Confirmed")                    # PendingReview, Confirmed

    batch_id: Optional[int] = Field(default=None, foreign_key="batchingestion.id", ondelete="SET NULL")
    batch: Optional[BatchIngestion] = Relationship(back_populates="transactions")

    id_from_account: Optional[int] = Field(default=None, foreign_key="account.id", ondelete="RESTRICT")
    account_from: Optional["Account"] = Relationship(
        back_populates="transactions_from",
        sa_relationship_kwargs={"foreign_keys": "Transaction.id_from_account"},
    )

    id_destination_account: Optional[int] = Field(default=None, foreign_key="account.id", ondelete="RESTRICT")
    account_destination: Optional["Account"] = Relationship(
        back_populates="transactions_destination",
        sa_relationship_kwargs={"foreign_keys": "Transaction.id_destination_account"},
    )

    category_id: Optional[int] = Field(default=None, foreign_key="category.id", ondelete="RESTRICT")
    category: Optional["Category"] = Relationship(back_populates="transactions")


class Debt(TenantBaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = Field(default=None)
    total_amount: Optional[float] = Field(default=None)
    minimum_payment: Optional[float] = Field(default=None)
    cutoff_day: int                                             # Day of month (1-31)
    due_day: int                                                # Payment day (1-31)
    interest_rate: Optional[float] = Field(default=None)


class FixedIncome(TenantBaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    amount: float
    frequency: str = Field(default="monthly")                   # weekly, biweekly, monthly, yearly
    payment_day: Optional[int] = Field(default=None)            # Day of month (1-31)
    id_destination_account: int = Field(foreign_key="account.id", ondelete="RESTRICT")

    payments: List["FixedIncomePayment"] = Relationship(back_populates="fixed_income")


class FixedIncomePayment(TenantBaseModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_fixed_income: int = Field(foreign_key="fixedincome.id", ondelete="RESTRICT")
    amount: float
    date: datetime
    confirmed: bool = Field(default=False)
    id_transaction: Optional[int] = Field(default=None, foreign_key="transaction.id", ondelete="SET NULL")

    fixed_income: Optional["FixedIncome"] = Relationship(back_populates="payments")
