from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import update

from src.domain.models import LedgerEntry


def test_full_flow(client, api_store):
    a = client.post("/accounts", json={"owner": "Ana", "initial_balance": "100.00"})
    b = client.post("/accounts", json={"owner": "Bia", "initial_balance": "0"})
    assert a.status_code == b.status_code == 201
    aid, bid = a.json()["id"], b.json()["id"]
    payload = {"source_id": aid, "destination_id": bid, "amount": "25", "idempotency_key": "abc"}
    transfer = client.post("/transfers", json=payload)
    assert transfer.status_code == 201
    assert transfer.json()["created"] is True
    assert client.post("/transfers", json=payload).json()["created"] is False
    assert float(client.get(f"/accounts/{aid}").json()["balance"]) == 75
    assert float(client.get(f"/accounts/{bid}").json()["balance"]) == 25
    debit = client.get(f"/accounts/{aid}/statement", params={"kind": "debit"})
    credit = client.get(f"/accounts/{bid}/statement", params={"kind": "credit"})
    assert debit.status_code == credit.status_code == 200
    assert len(debit.json()) == len(credit.json()) == 1
    # Persiste datas exatas para verificar o limite inicial, o final e exclusões dos dois lados.
    dates = {transfer.json()["id"]: 2}
    for day in (1, 3, 4):
        response = client.post("/transfers", json={
            **payload, "amount": str(day), "idempotency_key": f"date-{day}",
        })
        assert response.status_code == 201
        dates[response.json()["id"]] = day
    _, sessions = api_store
    with sessions.begin() as session:
        for transfer_id, day in dates.items():
            session.execute(update(LedgerEntry).where(LedgerEntry.transfer_id == transfer_id).values(
                created_at=datetime(2025, 1, day, tzinfo=timezone.utc),
            ))

    all_entries = client.get(f"/accounts/{aid}/statement").json()
    assert [entry["created_at"][:10] for entry in all_entries] == [
        "2025-01-02", "2025-01-01", "2025-01-03", "2025-01-04",
    ]
    period = client.get(f"/accounts/{aid}/statement", params={
        "start": "2025-01-02T00:00:00Z", "end": "2025-01-03T00:00:00Z", "kind": "debit",
    })
    assert period.status_code == 200
    assert [
        (entry["created_at"][:10], entry["kind"], Decimal(str(entry["amount"])))
        for entry in period.json()
    ] == [("2025-01-02", "debit", Decimal("25")), ("2025-01-03", "debit", Decimal("3"))]


def test_api_errors(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/accounts/999").status_code == 404
    assert client.get("/accounts/999/statement").status_code == 404
    assert client.post("/accounts", json={"owner": " ", "initial_balance": 0}).status_code == 400
    a = client.post("/accounts", json={"owner": "Ana", "initial_balance": 5}).json()["id"]
    b = client.post("/accounts", json={"owner": "Bia", "initial_balance": 0}).json()["id"]
    assert client.post("/transfers", json={"source_id": a, "destination_id": b, "amount": 100, "idempotency_key": "no"}).status_code == 400
    assert client.get(f"/accounts/{a}/statement", params={"kind": "other"}).status_code == 422
    assert client.get(f"/accounts/{a}/statement", params={"start": "2030-01-01T00:00:00", "end": "2020-01-01T00:00:00"}).status_code == 400
