from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.domain.models import Account, LedgerEntry
from src.domain.rules import DomainError
from src.repositories.database import get_db
from src.services.wallet import create_account, transfer_funds

router = APIRouter()


class AccountInput(BaseModel):
    owner: str = Field(min_length=1, max_length=100)
    initial_balance: Decimal = Decimal("0")


class TransferInput(BaseModel):
    source_id: int
    destination_id: int
    amount: Decimal
    idempotency_key: str = Field(min_length=1, max_length=100)


@router.post("/accounts", status_code=201)
def add_account(data: AccountInput, db: Session = Depends(get_db)):
    try:
        a = create_account(db, data.owner, data.initial_balance)
        return {"id": a.id, "owner": a.owner, "balance": a.balance}
    except DomainError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/accounts/{account_id}")
def get_account(account_id: int, db: Session = Depends(get_db)):
    a = db.get(Account, account_id)
    if not a:
        raise HTTPException(404, "Conta não encontrada")
    return {"id": a.id, "owner": a.owner, "balance": a.balance}


@router.post("/transfers", status_code=201)
def make_transfer(data: TransferInput, db: Session = Depends(get_db)):
    try:
        t, created = transfer_funds(db, data.source_id, data.destination_id, data.amount, data.idempotency_key)
        return {"id": t.id, "amount": t.amount, "created": created}
    except DomainError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/accounts/{account_id}/statement")
def statement(account_id: int, kind: str | None = Query(None, pattern="^(debit|credit)$"),
              start: datetime | None = None, end: datetime | None = None, db: Session = Depends(get_db)):
    if not db.get(Account, account_id):
        raise HTTPException(404, "Conta não encontrada")
    if start and end and start > end:
        raise HTTPException(400, "Período inválido")
    stmt = select(LedgerEntry).where(LedgerEntry.account_id == account_id)
    if kind:
        stmt = stmt.where(LedgerEntry.kind == kind)
    if start:
        stmt = stmt.where(LedgerEntry.created_at >= start)
    if end:
        stmt = stmt.where(LedgerEntry.created_at <= end)
    entries = db.scalars(stmt.order_by(LedgerEntry.id)).all()
    return [{"id": e.id, "kind": e.kind, "amount": e.amount, "created_at": e.created_at} for e in entries]
