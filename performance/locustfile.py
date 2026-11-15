"""Execute: locust -f performance/locustfile.py --host http://127.0.0.1:8000"""
import uuid
from locust import HttpUser, between, task


class WalletUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.source = self.client.post("/accounts", json={"owner": "Load Source", "initial_balance": "100000"}).json()["id"]
        self.destination = self.client.post("/accounts", json={"owner": "Load Target", "initial_balance": "0"}).json()["id"]

    @task
    def transfer(self):
        self.client.post("/transfers", json={
            "source_id": self.source, "destination_id": self.destination,
            "amount": "1", "idempotency_key": str(uuid.uuid4()),
        }, name="POST /transfers")
