"""Disputas HTTP com sessões e conexões SQLite separadas."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import event, select

from src.domain.models import Account, LedgerEntry, Transfer
from src.services.wallet import create_account


@pytest.mark.parametrize(("same_key", "initial_balance"), [
    pytest.param(False, "10", id="disputa-saldo"),
    pytest.param(True, "10", id="mesma-chave-saldo-esgotado"),
    pytest.param(True, "20", id="mesma-chave-violacao-unique"),
])
def test_concurrent_transfers(client, api_store, same_key, initial_balance):
    engine, sessions = api_store
    with sessions() as session:
        source = create_account(session, "Origem", Decimal(initial_balance))
        destination = create_account(session, "Destino", Decimal("0"))
        source_id, destination_id = source.id, destination.id

    # Faz ambas passarem pela consulta de idempotência antes do primeiro débito.
    debit_barrier = Barrier(2, timeout=8)
    connections = set()

    def synchronize_before_debit(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("UPDATE ACCOUNTS") and ">=" in statement:
            connections.add(id(conn.connection.driver_connection))
            debit_barrier.wait()

    def confirm_committed(transfer):
        with sessions() as session:
            assert session.get(Transfer, transfer.id) is not None
            assert len(session.scalars(select(LedgerEntry).where(LedgerEntry.transfer_id == transfer.id)).all()) == 2

    def send(key):
        return client.post("/transfers", json={
            "source_id": source_id, "destination_id": destination_id,
            "amount": "10.00", "idempotency_key": key,
        })

    notifier = Mock()
    notifier.notify.side_effect = confirm_committed
    event.listen(engine, "before_cursor_execute", synchronize_before_debit)
    try:
        with patch("src.services.wallet.Notifier", return_value=notifier):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(send, "first")
                second = pool.submit(send, "first" if same_key else "second")
                responses = [first.result(timeout=20), second.result(timeout=20)]
    finally:
        event.remove(engine, "before_cursor_execute", synchronize_before_debit)

    assert len(connections) == 2
    assert sorted(response.status_code for response in responses) == ([201, 201] if same_key else [201, 400])
    accepted = [response.json() for response in responses if response.status_code == 201]
    assert sum(item["created"] for item in accepted) == 1
    if not same_key:
        assert next(r for r in responses if r.status_code == 400).json() == {"detail": "Saldo insuficiente"}

    with sessions() as session:
        assert session.get(Account, source_id).balance == Decimal(initial_balance) - Decimal("10")
        assert session.get(Account, destination_id).balance == Decimal("10")
        (transfer,) = session.scalars(select(Transfer)).all()
        entries = session.scalars(select(LedgerEntry)).all()
        assert len(entries) == 2
        assert {(entry.account_id, entry.kind, entry.amount, entry.transfer_id) for entry in entries} == {
            (source_id, "debit", Decimal("10"), transfer.id),
            (destination_id, "credit", Decimal("10"), transfer.id),
        }
        assert {item["id"] for item in accepted} == {transfer.id}

    notifier.notify.assert_called_once()
    assert notifier.notify.call_args.args[0].id == transfer.id
