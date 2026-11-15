"""Compara a série de intervalos ASGI com as métricas HTTP registradas pelo Locust."""
import argparse
import json
from pathlib import Path


def summarize(stats, trace):
    rows = json.loads(Path(stats).read_text(encoding="utf-8"))
    row = next((r for r in rows if r["name"] == "POST /transfers" and r["method"] == "POST"), None)
    if not row or not row["num_requests"]:
        raise ValueError("O Locust não registrou chamadas a POST /transfers.")
    count = row["num_requests"]
    failures = row["num_failures"]
    events = []
    statuses = {}
    with Path(trace).open(encoding="utf-8-sig") as stream:
        for line in stream:
            if line.startswith("TRANSFER_TRACE "):
                interval = json.loads(line.removeprefix("TRANSFER_TRACE "))
                events.extend([(interval["start_ns"], 1), (interval["end_ns"], -1)])
                status = str(interval["status"])
                statuses[status] = statuses.get(status, 0) + 1

    # Em empate de tempo, processa o término antes de um novo início.
    in_flight = peak = 0
    for _, delta in sorted(events):
        in_flight += delta
        peak = max(peak, in_flight)
    return {
        "endpoint": "POST /transfers",
        "requests_locust": count,
        "failures_locust": failures,
        "error_rate_percent": round(100 * failures / count, 2),
        "mean_latency_ms": round(row["total_response_time"] / count, 2),
        "requests_observed_server": len(events) // 2,
        "peak_concurrent_server": peak,
        "server_statuses": statuses,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stats")
    parser.add_argument("trace")
    args = parser.parse_args()
    result = summarize(args.stats, args.trace)
    print(json.dumps(result, indent=2))
    if not (
        result["requests_locust"] == result["requests_observed_server"]
        and result["peak_concurrent_server"] >= 50
        and result["failures_locust"] == 0
        and result["server_statuses"] == {"201": result["requests_locust"]}
    ):
        parser.exit(1, "A rodada não cumpriu todos os critérios. Confira métricas e logs.\n")
