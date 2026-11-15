"""Uma rajada sincronizada de 64 POSTs, com contas criadas fora das métricas."""
from uuid import uuid4

import gevent
import requests
from urllib3 import PoolManager
from gevent.event import Event
from locust import HttpUser, events, task
from locust.exception import StopUser

BURST_SIZE = 64
account_ids = ()


@events.test_start.add_listener
def prepare_accounts(environment, **kwargs):
    global account_ids
    account_ids = ()
    if environment.parsed_options.num_users != 1:
        environment.process_exit_code = 2
        print("Use -u 1: um coordenador dispara 64 requisições em paralelo.", flush=True)
        return
    with requests.Session() as session:
        ids = []
        for owner, balance in (("Locust Origem", "100000"), ("Locust Destino", "0")):
            response = session.post(
                f"{environment.host.rstrip('/')}/accounts",
                json={"owner": owner, "initial_balance": balance},
                timeout=10,
            )
            response.raise_for_status()
            ids.append(response.json()["id"])
    account_ids = tuple(ids)


class WalletUser(HttpUser):
    pool_manager = PoolManager(num_pools=1, maxsize=BURST_SIZE, block=True)

    @task
    def transfer_burst(self):
        if not account_ids:
            self.environment.process_exit_code = 2
            gevent.spawn(self.environment.runner.quit)
            raise StopUser()
        gate = Event()
        source, destination = account_ids

        def send_transfer():
            key = str(uuid4())
            gate.wait()
            with self.client.post("/transfers", json={
                "source_id": source, "destination_id": destination,
                "amount": "1.00", "idempotency_key": key,
            }, name="POST /transfers", timeout=20, catch_response=True) as response:
                if response.status_code != 201:
                    response.failure(f"HTTP {response.status_code}")
                elif response.json().get("created") is not True:
                    response.failure("A transferência não foi criada")

        requests_in_flight = [gevent.spawn(send_transfer) for _ in range(BURST_SIZE)]
        gevent.sleep(0)  # Todas as greenlets chegam à barreira antes de abrir a rajada.
        gate.set()
        gevent.joinall(requests_in_flight, raise_error=True)
        gevent.spawn(self.environment.runner.quit)
        raise StopUser()
