def test_full_flow(client):
    a = client.post("/accounts", json={"owner": "Ana", "initial_balance": "100.00"})
    b = client.post("/accounts", json={"owner": "Bia", "initial_balance": "0"})
    assert a.status_code == b.status_code == 201
    aid, bid = a.json()["id"], b.json()["id"]
    payload = {"source_id": aid, "destination_id": bid, "amount": "25", "idempotency_key": "abc"}
    assert client.post("/transfers", json=payload).status_code == 201
    assert client.post("/transfers", json=payload).json()["created"] is False
    assert float(client.get(f"/accounts/{aid}").json()["balance"]) == 75
    assert float(client.get(f"/accounts/{bid}").json()["balance"]) == 25
    debit = client.get(f"/accounts/{aid}/statement", params={"kind": "debit"})
    credit = client.get(f"/accounts/{bid}/statement", params={"kind": "credit"})
    assert debit.status_code == credit.status_code == 200
    assert len(debit.json()) == len(credit.json()) == 1
    assert client.get(f"/accounts/{aid}/statement", params={"start": "2020-01-01T00:00:00", "end": "2030-01-01T00:00:00"}).status_code == 200


def test_api_errors(client):
    assert client.get("/accounts/999").status_code == 404
    assert client.get("/accounts/999/statement").status_code == 404
    assert client.post("/accounts", json={"owner": " ", "initial_balance": 0}).status_code == 400
    a = client.post("/accounts", json={"owner": "Ana", "initial_balance": 5}).json()["id"]
    b = client.post("/accounts", json={"owner": "Bia", "initial_balance": 0}).json()["id"]
    assert client.post("/transfers", json={"source_id": a, "destination_id": b, "amount": 100, "idempotency_key": "no"}).status_code == 400
    assert client.get(f"/accounts/{a}/statement", params={"kind": "other"}).status_code == 422
    assert client.get(f"/accounts/{a}/statement", params={"start": "2030-01-01T00:00:00", "end": "2020-01-01T00:00:00"}).status_code == 400
