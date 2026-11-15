from decimal import Decimal
from unittest.mock import Mock
import httpx
import pytest
from sqlalchemy import select
from src.domain.models import Account, LedgerEntry, Transfer
from src.domain.rules import DomainError
from src.services.wallet import create_account, transfer_funds


WEBHOOK_URL = "http://127.0.0.1:9001/antifraud"


def test_mock_antifraud_receives_committed_transfer_only_once(db, monkeypatch):
    a = create_account(db, "Ana", Decimal("100"))
    b = create_account(db, "Bia", Decimal("0"))
    response = Mock()
    post = Mock(return_value=response)
    monkeypatch.setenv("ANTIFRAUD_WEBHOOK_URL", WEBHOOK_URL)
    monkeypatch.setattr("src.services.wallet.httpx.post", post)

    transfer, created = transfer_funds(db, a.id, b.id, Decimal("25"), "key-1")
    assert created
    _, created_again = transfer_funds(db, a.id, b.id, Decimal("25"), "key-1")
    assert not created_again
    post.assert_called_once_with(WEBHOOK_URL, json={
        "event": "transfer.confirmed",
        "transfer_id": transfer.id,
        "source_id": a.id,
        "destination_id": b.id,
        "amount": "25.00",
    }, timeout=2.0)
    response.raise_for_status.assert_called_once_with()
    assert db.get(Account, a.id).balance == 75
    assert db.get(Account, b.id).balance == 25
    assert len(db.scalars(select(LedgerEntry)).all()) == 2


def test_webhook_timeout_does_not_undo_committed_transfer(db, monkeypatch, caplog):
    a = create_account(db, "Ana", Decimal("20"))
    b = create_account(db, "Bia", Decimal("0"))
    post = Mock(side_effect=httpx.ConnectTimeout("tempo esgotado"))
    monkeypatch.setenv("ANTIFRAUD_WEBHOOK_URL", WEBHOOK_URL)
    monkeypatch.setattr("src.services.wallet.httpx.post", post)

    transfer, created = transfer_funds(db, a.id, b.id, Decimal("10"), "timeout")
    assert created
    db.expire_all()
    assert db.get(Transfer, transfer.id) is not None
    assert db.get(Account, a.id).balance == 10
    assert db.get(Account, b.id).balance == 10
    assert "Webhook antifraude falhou" in caplog.text
    assert transfer_funds(db, a.id, b.id, Decimal("10"), "timeout")[1] is False
    post.assert_called_once()


class RejectedRegistrationStub:
    def is_valid(self, owner: str) -> bool:
        return False


def test_stub_registration(db):
    with pytest.raises(DomainError, match="Cadastro"):
        create_account(db, "Ana", Decimal("5"), RejectedRegistrationStub())
    assert db.scalars(select(Account)).all() == []


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
