#!/usr/bin/env python3
"""Timing harness for the modulo-210 wheel sieve.

Times ./sieve --count, so the measurement covers the sieve itself rather than
the cost of formatting tens of thousands of numbers.

./sieve does one pass per process, so a single run is swamped by ~2ms of fork,
exec and dyld. --repeat runs the sieve many times in one process, so that fixed
cost is divided away: at -r 200 a 2ms startup contributes 0.01ms per pass.
reference/mod30 self-times in-process for the same reason, which makes the two
columns directly comparable.

Usage:
    python3 bench.py [limit ...] [-n RUNS] [--print]
"""

import argparse
import os
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BINARY = os.path.join(HERE, "sieve")
REFERENCE = os.path.join(HERE, "reference", "mod30")

DEFAULT_LIMITS = [1000000]


def time_run(limit, repeat=1, count_only=True):
    """One process running the sieve `repeat` times. Returns wall seconds."""
    argv = [BINARY, "--repeat", str(repeat)]
    if count_only:
        argv.append("--count")
    argv.append(str(limit))
    with open(os.devnull, "wb") as devnull:
        start = time.perf_counter()
        proc = subprocess.run(argv, stdout=devnull, stderr=subprocess.PIPE)
        elapsed = time.perf_counter() - start
    if proc.returncode != 0:
        sys.exit(f"sieve {limit} failed with status {proc.returncode}")
    return elapsed


def passes_for(limit):
    """Enough repeats that startup is noise: aim for ~0.5s of real work."""
    return max(3, min(2000, int(2e8 / max(limit, 1))))


def per_pass(limit, runs, count_only=True):
    """Best per-pass seconds, with the one-off startup cost divided away."""
    n = passes_for(limit)
    time_run(limit, n, count_only)                  # warm caches, discard
    best = min(time_run(limit, n, count_only) for _ in range(runs))
    startup = min(time_run(0, 1) for _ in range(5))
    return max(best - startup, 0.0) / n


def count_primes(limit):
    out = subprocess.run([BINARY, "--count", str(limit)],
                         capture_output=True, text=True)
    return int(out.stdout.rsplit(":", 1)[1])


def reference_ms(limit, secs=2):
    """reference/mod30 times itself; return ms per pass, or None if unbuilt."""
    if not os.path.exists(REFERENCE):
        return None
    out = subprocess.run([REFERENCE, "--secs", str(secs), "--size", str(limit)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    fields = out.stdout.strip().split(";")
    passes, elapsed = int(fields[1]), float(fields[2])
    return elapsed * 1000 / passes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("limits", nargs="*", type=int, default=DEFAULT_LIMITS)
    parser.add_argument("-n", "--runs", type=int, default=10,
                        help="timed runs per limit (default 10)")
    parser.add_argument("--print", dest="do_print", action="store_true",
                        help="also time the full prime listing")
    args = parser.parse_args()

    if not os.path.exists(BINARY):
        sys.exit("./sieve not built -- run 'make' first")

    cols = (f"{'limit':>12}  {'primes':>8}  {'passes':>7}  {'sieve':>10}  "
            f"{'n/sec':>14}")
    if os.path.exists(REFERENCE):
        cols += f"  {'mod30':>9}  {'speedup':>8}"
    if args.do_print:
        cols += f"  {'+listing':>9}"
    print(cols)
    print("-" * len(cols))

    for limit in args.limits:
        work = per_pass(limit, args.runs)
        row = (f"{limit:>12,}  {count_primes(limit):>8,}  {passes_for(limit):>7,}  "
               f"{work * 1000:>8.4f}ms  {limit / work:>14,.0f}")

        ref = reference_ms(limit)
        if ref is not None:
            row += f"  {ref:>8.4f}ms  {ref / (work * 1000):>7.2f}x"

        if args.do_print:
            # Listing happens once per process regardless of --repeat, so it
            # cannot be divided down. Take the delta against --count instead:
            # both runs pay one startup and one sieve, so what is left is the
            # cost of formatting the primes.
            runs = max(3, args.runs // 3)
            listed = min(time_run(limit, 1, False) for _ in range(runs))
            counted = min(time_run(limit, 1, True) for _ in range(runs))
            row += f"  {max(listed - counted, 0.0) * 1000:>9.2f}ms"

        print(row)


if __name__ == "__main__":
    sys.exit(main())
