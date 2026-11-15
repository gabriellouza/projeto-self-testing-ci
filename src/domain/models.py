from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class Transfer(Base):
    __tablename__ = "transfers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    destination_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    transfer_id: Mapped[int] = mapped_column(ForeignKey("transfers.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
