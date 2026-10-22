"""
Phase 8B smoke load test against a running Streamlit app.

Usage:
  streamlit run Home.py
  python load_test_smoke.py --users 50 --requests 2
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests


def hit(url: str, timeout: int = 20) -> float:
    start = time.perf_counter()
    response = requests.get(url, timeout=timeout)
    elapsed = time.perf_counter() - start
    if response.status_code >= 500:
        raise RuntimeError(f"HTTP {response.status_code} from {url}")
    return elapsed


def run_url(url: str, users: int, requests_per_user: int) -> dict:
    total = users * requests_per_user
    times = []
    errors = 0
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=users) as pool:
        futures = [pool.submit(hit, url) for _ in range(total)]
        for future in as_completed(futures):
            try:
                times.append(future.result())
            except Exception:
                errors += 1
    duration = time.perf_counter() - started
    ok = len(times)
    return {
        "url": url,
        "total": total,
        "success": ok,
        "errors": errors,
        "error_rate": (errors / total) if total else 0,
        "avg_s": statistics.mean(times) if times else None,
        "p95_s": (statistics.quantiles(times, n=20)[18] if len(times) >= 20 else (max(times) if times else None)),
        "duration_s": duration,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8501")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--requests", type=int, default=2)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    urls = [
        urljoin(args.base_url.rstrip("/") + "/", "_stcore/health"),
        args.base_url.rstrip("/") + "/",
    ]

    print(f"50-user style test: {args.users} workers x {args.requests} hits")
    results = [run_url(url, args.users, args.requests) for url in urls]
    for row in results:
        print("")
        print(row["url"])
        print(f"  success {row['success']}/{row['total']}  errors {row['error_rate']:.1%}")
        print(f"  avg {row['avg_s']:.3f}s  p95 {row['p95_s']:.3f}s" if row["avg_s"] is not None else "  no successful samples")

    failed = any(r["error_rate"] > 0.01 or (r["avg_s"] or 99) > 3 for r in results)
    print("")
    print("Targets: error rate < 1%, average < 3s (health/home). Upload concurrency is not included.")
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump({"users": args.users, "requests": args.requests, "results": results}, handle, indent=2)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
