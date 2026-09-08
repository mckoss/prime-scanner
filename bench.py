#!/usr/bin/env python3
"""Timing harness for the modulo-210 wheel sieve.

Times ./sieve --count, so the measurement covers the sieve itself rather than
the cost of formatting tens of thousands of numbers. The --print column shows
what the full listing costs on top, for comparison.

Usage:
    python3 bench.py [limit ...] [-n RUNS]
"""

import argparse
import os
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BINARY = os.path.join(HERE, "sieve")

DEFAULT_LIMITS = [1000000]


def time_run(limit, count_only=True):
    """One run of ./sieve <limit>. Returns seconds."""
    argv = [BINARY, "--count", str(limit)] if count_only else [BINARY, str(limit)]
    with open(os.devnull, "wb") as devnull:
        start = time.perf_counter()
        proc = subprocess.run(argv, stdout=devnull, stderr=subprocess.PIPE)
        elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        sys.exit(f"sieve {limit} failed with status {proc.returncode}")
    return elapsed


def count_primes(limit):
    out = subprocess.run([BINARY, "--count", str(limit)],
                         capture_output=True, text=True)
    return int(out.stdout.rsplit(":", 1)[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("limits", nargs="*", type=int, default=DEFAULT_LIMITS)
    parser.add_argument("-n", "--runs", type=int, default=10,
                        help="timed runs per limit (default 10)")
    args = parser.parse_args()

    if not os.path.exists(BINARY):
        sys.exit("./sieve not built -- run 'make' first")

    print(f"{'limit':>12}  {'primes':>8}  {'best':>9}  {'median':>9}  "
          f"{'mean':>9}  {'n/sec':>14}  {'+print':>9}")
    print("-" * 82)

    for limit in args.limits:
        time_run(limit)                       # warm the caches, discard
        times = [time_run(limit) for _ in range(args.runs)]
        best, med = min(times), statistics.median(times)
        mean = statistics.fmean(times)

        time_run(limit, count_only=False)
        printed = min(time_run(limit, count_only=False)
                      for _ in range(max(3, args.runs // 3)))

        print(f"{limit:>12,}  {count_primes(limit):>8,}  {best * 1000:>7.1f}ms  "
              f"{med * 1000:>7.1f}ms  {mean * 1000:>7.1f}ms  "
              f"{limit / best:>14,.0f}  {printed * 1000:>7.1f}ms")


if __name__ == "__main__":
    sys.exit(main())
