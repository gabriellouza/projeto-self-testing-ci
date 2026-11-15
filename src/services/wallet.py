from decimal import Decimal
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from src.domain.models import Account, Transfer, LedgerEntry
from src.domain.rules import DomainError, validate_amount


class Notifier:
    def notify(self, transfer: Transfer) -> None:
        """Gateway fictício: substituível por mock; não faz chamadas externas."""
        return None


class RegistrationStub:
    def is_valid(self, owner: str) -> bool:
        return bool(owner.strip())


def create_account(db: Session, owner: str, initial_balance: Decimal, validator=None):
    validator = validator or RegistrationStub()
    if not validator.is_valid(owner):
        raise DomainError("Cadastro inválido")
    if not initial_balance.is_finite() or initial_balance < 0 or initial_balance.as_tuple().exponent < -2:
        raise DomainError("Saldo inicial inválido")
    account = Account(owner=owner, balance=initial_balance)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def transfer_funds(db: Session, source_id: int, destination_id: int, amount: Decimal, key: str, notifier=None):
    validate_amount(amount)
    if source_id == destination_id:
        raise DomainError("Contas devem ser diferentes")
    if not key.strip():
        raise DomainError("Chave de idempotência obrigatória")
    existing = db.scalar(select(Transfer).where(Transfer.idempotency_key == key))
    if existing:
        if (existing.source_id, existing.destination_id, existing.amount) != (source_id, destination_id, amount):
            raise DomainError("Chave de idempotência reutilizada com outros dados")
        return existing, False
    try:
        # UPDATE condicional é atômico: duas transferências não podem gastar o mesmo saldo.
        result = db.execute(update(Account).where(Account.id == source_id, Account.balance >= amount).values(balance=Account.balance - amount))
        if result.rowcount != 1:
            if not db.get(Account, source_id):
                raise DomainError("Conta de origem inexistente")
            raise DomainError("Saldo insuficiente")
        result = db.execute(update(Account).where(Account.id == destination_id).values(balance=Account.balance + amount))
        if result.rowcount != 1:
            raise DomainError("Conta de destino inexistente")
        item = Transfer(source_id=source_id, destination_id=destination_id, amount=amount, idempotency_key=key)
        db.add(item)
        db.flush()
        db.add_all([
            LedgerEntry(account_id=source_id, transfer_id=item.id, kind="debit", amount=amount),
            LedgerEntry(account_id=destination_id, transfer_id=item.id, kind="credit", amount=amount),
        ])
        db.commit()
        db.refresh(item)
    except (DomainError, IntegrityError, OperationalError):
        db.rollback()
        # Em disputa pela mesma chave, a transação vencedora pode já ter concluído.
        winner = db.scalar(select(Transfer).where(Transfer.idempotency_key == key))
        if winner:
            if (winner.source_id, winner.destination_id, winner.amount) != (source_id, destination_id, amount):
                raise DomainError("Chave de idempotência reutilizada com outros dados")
            return winner, False
        raise
    (notifier or Notifier()).notify(item)
    return item, True
