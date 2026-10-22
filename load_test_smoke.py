"""
Phase 8 smoke load test against a running Streamlit app.

Usage:
  streamlit run Home.py
  python load_test_smoke.py --url http://localhost:8501 --users 20 --requests 5
"""

from __future__ import annotations

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


def hit(url: str) -> float:
    start = time.perf_counter()
    response = requests.get(url, timeout=15)
    elapsed = time.perf_counter() - start
    if response.status_code >= 500:
        raise RuntimeError(f"HTTP {response.status_code}")
    return elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8501/_stcore/health")
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--requests", type=int, default=5)
    args = parser.parse_args()

    total = args.users * args.requests
    print(f"Hitting {args.url} with {args.users} workers x {args.requests} requests ({total} total)")

    times = []
    errors = 0
    started = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.users) as pool:
        futures = [pool.submit(hit, args.url) for _ in range(total)]
        for future in as_completed(futures):
            try:
                times.append(future.result())
            except Exception as exc:
                errors += 1
                print(f"  error: {exc}")

    duration = time.perf_counter() - started
    ok = len(times)
    error_rate = errors / total if total else 0
    avg = statistics.mean(times) if times else 0
    p95 = statistics.quantiles(times, n=20)[18] if len(times) >= 20 else (max(times) if times else 0)

    print("")
    print(f"Completed in {duration:.2f}s")
    print(f"Success: {ok}/{total}")
    print(f"Error rate: {error_rate:.1%}")
    print(f"Average latency: {avg:.3f}s")
    print(f"p95 latency: {p95:.3f}s")
    print("")
    print("Targets: error rate < 1%, page load < 2s average, health < 3s")
    if error_rate > 0.01 or avg > 3:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
