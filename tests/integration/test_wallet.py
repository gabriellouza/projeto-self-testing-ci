from decimal import Decimal
from unittest.mock import Mock
import pytest
from sqlalchemy import select
from src.domain.models import Account, LedgerEntry, Transfer
from src.domain.rules import DomainError
from src.services.wallet import create_account, transfer_funds


def test_mock_notifier_called_once_with_transfer(db):
    a = create_account(db, "Ana", Decimal("100"))
    b = create_account(db, "Bia", Decimal("0"))
    notifier = Mock()
    transfer, created = transfer_funds(db, a.id, b.id, Decimal("25"), "key-1", notifier)
    assert created
    notifier.notify.assert_called_once_with(transfer)
    assert db.get(Account, a.id).balance == 75
    assert db.get(Account, b.id).balance == 25
    assert len(db.scalars(select(LedgerEntry)).all()) == 2
    _, created_again = transfer_funds(db, a.id, b.id, Decimal("25"), "key-1", notifier)
    assert not created_again
    notifier.notify.assert_called_once()


def test_stub_registration(db):
    validator = Mock()
    validator.is_valid.return_value = False
    with pytest.raises(DomainError, match="Cadastro"):
        create_account(db, "Ana", Decimal("5"), validator)
    validator.is_valid.assert_called_once_with("Ana")


@pytest.mark.parametrize("balance", [Decimal("-1"), Decimal("1.234"), Decimal("NaN")])
def test_invalid_initial_balance(db, balance):
    with pytest.raises(DomainError):
        create_account(db, "Ana", balance)


def test_invalid_registration(db):
    with pytest.raises(DomainError):
        create_account(db, "  ", Decimal("0"))


def test_transfer_rejections(db):
    a = create_account(db, "Ana", Decimal("10"))
    b = create_account(db, "Bia", Decimal("0"))
    with pytest.raises(DomainError, match="diferentes"):
        transfer_funds(db, a.id, a.id, Decimal("1"), "a")
    with pytest.raises(DomainError, match="obrigatória"):
        transfer_funds(db, a.id, b.id, Decimal("1"), " ")
    with pytest.raises(DomainError, match="insuficiente"):
        transfer_funds(db, a.id, b.id, Decimal("100"), "b")
    with pytest.raises(DomainError, match="origem inexistente"):
        transfer_funds(db, 999, b.id, Decimal("1"), "c")
    with pytest.raises(DomainError, match="destino inexistente"):
        transfer_funds(db, a.id, 999, Decimal("1"), "d")
    assert db.get(Account, a.id).balance == 10


def test_idempotency_conflict(db):
    a = create_account(db, "Ana", Decimal("50"))
    b = create_account(db, "Bia", Decimal("0"))
    transfer_funds(db, a.id, b.id, Decimal("5"), "same")
    with pytest.raises(DomainError, match="reutilizada"):
        transfer_funds(db, a.id, b.id, Decimal("6"), "same")
    assert len(db.scalars(select(Transfer)).all()) == 1
