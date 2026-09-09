#!/usr/bin/env python3
"""Test harness for the modulo-210 wheel sieve.

Every test compares the *exact* prime list the binary prints against an
independently computed one. Counting primes is not enough: a wheel bug that
drops one prime and invents another keeps pi(n) intact while the output is
wrong, and this program has had exactly that class of bug.

Usage:
    python3 test_sieve.py [-v] [--slow]
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BINARY = os.path.join(HERE, "sieve")   # overridden by --binary

MODULUS = 210            # the wheel circumference, 2*3*5*7
WHEEL_SLOTS = 48         # phi(210), and BLOCK_BYTES * 8
BASE_PRIMES = (2, 3, 5, 7)
DEFAULT_LIMIT = 500

TESTS = []


def test(fn):
    """Register a test function. Its docstring is the reported name."""
    TESTS.append(fn)
    return fn


# --------------------------------------------------------------------------
# Reference implementations, deliberately unrelated to the code under test
# --------------------------------------------------------------------------

def reference_primes(n):
    """Plain Eratosthenes sieve over all integers. No wheel, no bit packing."""
    if n < 2:
        return []
    flags = bytearray([1]) * (n + 1)
    flags[0] = flags[1] = 0
    for i in range(2, int(n ** 0.5) + 1):
        if flags[i]:
            flags[i * i::i] = bytearray(len(range(i * i, n + 1, i)))
    return [i for i, is_p in enumerate(flags) if is_p]


def reference_window(lo, hi):
    """Segmented reference: primes in [lo, hi], computed without a wheel."""
    if hi < 2 or lo > hi:
        return []
    lo = max(lo, 0)
    root = int(hi ** 0.5) + 1
    base = reference_primes(root)

    flags = bytearray([1]) * (hi - lo + 1)
    for v in (0, 1):
        if lo <= v <= hi:
            flags[v - lo] = 0
    for p in base:
        start = max(p * p, ((lo + p - 1) // p) * p)
        for m in range(start, hi + 1, p):
            flags[m - lo] = 0
    return [lo + i for i, f in enumerate(flags) if f]


def is_prime_miller_rabin(n):
    """Deterministic for n < 3.3e24, so it covers the whole 64-bit range."""
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in small:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def is_prime_by_trial_division(n):
    """Second opinion that shares no logic with either sieve."""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    f = 3
    while f * f <= n:
        if n % f == 0:
            return False
        f += 2
    return True


# --------------------------------------------------------------------------
# Driving the binary
# --------------------------------------------------------------------------

class SieveError(AssertionError):
    pass


def run_sieve(*args, timeout=120):
    """Invoke ./sieve and return the CompletedProcess."""
    try:
        return subprocess.run([BINARY, *args], capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise SieveError(f"sieve {' '.join(args)}: timed out after {timeout}s")
    except OSError as exc:
        raise SieveError(f"cannot execute {BINARY}: {exc}")


def primes_from(limit, timeout=120):
    """Run the sieve for `limit` and parse its prime list, checking the frame."""
    proc = run_sieve(str(limit), timeout=timeout)

    if proc.returncode != 0:
        raise SieveError(f"sieve {limit}: exit status {proc.returncode}, "
                         f"stderr={proc.stderr.strip()!r}")
    if proc.stderr:
        raise SieveError(f"sieve {limit}: unexpected stderr {proc.stderr.strip()!r}")

    lines = proc.stdout.strip().split("\n")
    expected_header = f"Primes up to {limit}:"
    if lines[0] != expected_header:
        raise SieveError(f"sieve {limit}: header was {lines[0]!r}, "
                         f"expected {expected_header!r}")

    tokens = " ".join(lines[1:]).split()
    try:
        return [int(t) for t in tokens]
    except ValueError:
        bad = [t for t in tokens if not t.lstrip("-").isdigit()]
        raise SieveError(f"sieve {limit}: non-numeric output {bad[:5]}")


def count_from(limit, *flags, timeout=120):
    """Run the sieve in --count mode and parse the single reported total."""
    proc = run_sieve(*flags, str(limit), timeout=timeout)

    if proc.returncode != 0:
        raise SieveError(f"sieve {' '.join(flags)} {limit}: exit status "
                         f"{proc.returncode}, stderr={proc.stderr.strip()!r}")

    text = proc.stdout.strip()
    expected_prefix = f"Primes up to {limit}: "
    if not text.startswith(expected_prefix) or "\n" in text:
        raise SieveError(f"sieve --count {limit}: expected a single line "
                         f"{expected_prefix + '<n>'!r}, got {text!r}")
    try:
        return int(text[len(expected_prefix):])
    except ValueError:
        raise SieveError(f"sieve --count {limit}: total is not a number: {text!r}")


def window_from(lo, hi, *flags, timeout=60):
    """Run the sieve over a window and parse its prime list."""
    proc = run_sieve(*flags, "--from", str(lo), str(hi), timeout=timeout)
    if proc.returncode != 0:
        raise SieveError(f"sieve --from {lo} {hi}: exit {proc.returncode}, "
                         f"stderr={proc.stderr.strip()!r}")

    lines = proc.stdout.strip().split("\n")
    expected = f"Primes from {lo} to {hi}:"
    if lines[0] != expected:
        raise SieveError(f"sieve --from {lo} {hi}: header was {lines[0]!r}, "
                         f"expected {expected!r}")
    return [int(x) for x in " ".join(lines[1:]).split()]


def check_window(lo, hi, timeout=60):
    """Assert the window's output matches the segmented reference exactly."""
    actual = window_from(lo, hi, timeout=timeout)
    expected = reference_window(lo, hi)
    if actual == expected:
        return

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    detail = [f"sieve --from {lo} {hi}: window does not match the reference",
              f"  printed {len(actual)} values, expected {len(expected)}"]
    if missing:
        detail.append(f"  missing: {missing[:10]}")
    if extra:
        detail.append(f"  should not be there: {extra[:10]}")
    if not missing and not extra:
        detail.append("  same values but wrong order")
    raise SieveError("\n".join(detail))


def check_exact(limit, timeout=120):
    """Assert the printed list is exactly the reference list, in order."""
    actual = primes_from(limit, timeout=timeout)
    expected = reference_primes(limit)
    if actual == expected:
        return

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    detail = [f"sieve {limit}: output does not match the reference sieve",
              f"  printed {len(actual)} values, expected {len(expected)}"]
    if missing:
        detail.append(f"  missing primes: {missing[:10]}"
                      + (f" (+{len(missing) - 10} more)" if len(missing) > 10 else ""))
    if extra:
        detail.append(f"  composites printed: {extra[:10]}"
                      + (f" (+{len(extra) - 10} more)" if len(extra) > 10 else ""))
    if not missing and not extra:
        detail.append("  same values but wrong order")
    raise SieveError("\n".join(detail))


# --------------------------------------------------------------------------
# Correctness across the number line
# --------------------------------------------------------------------------

@test
def test_exhaustive_small_limits():
    """Exact prime list for every limit 0..300"""
    # Sweeps the whole small-input surface in one go: the limit < 8 shortcut
    # in main(), an empty result, the first wheel block, the first block
    # boundary at 210, and the squares 121/169/289.
    for limit in range(0, 301):
        check_exact(limit, timeout=10)


@test
def test_block_boundaries():
    """Limits straddling multiples of the 210 wheel block"""
    # Block indexing (limit / MODULUS, and the loop's break conditions) is
    # easiest to get wrong exactly where one block ends and the next begins.
    for k in range(1, 13):
        edge = k * MODULUS
        for limit in (edge - 1, edge, edge + 1):
            check_exact(limit, timeout=10)


@test
def test_limit_equal_to_square_of_wheel_prime():
    """Limits at p*p, where a low floor(sqrt) would leave p*p unmarked"""
    # Regression: floor(sqrt(limit)) computed in floating point can land one
    # low (notably under -ffast-math), so the largest sieving prime never runs
    # and its square is reported as prime. limit == p*p is the exact tripwire.
    wheel_primes = [p for p in reference_primes(60) if p not in BASE_PRIMES]
    assert wheel_primes, "no wheel primes selected -- test would be vacuous"
    for p in wheel_primes:
        square = p * p
        for limit in (square - 1, square, square + 1):
            check_exact(limit, timeout=10)


@test
def test_primes_at_wheel_residue_one():
    """Primes congruent to 1 mod 210 are not dropped"""
    # Regression: residue 1 was excluded from the wheel as "1 is not prime",
    # which also discarded 211, 421, 631, ... and left the table one slot
    # short of the 48 the bit packing assumes.
    limit = 5000
    expected = [p for p in reference_primes(limit) if p % MODULUS == 1]
    assert expected, "no residue-1 primes in range -- test would be vacuous"

    printed = set(primes_from(limit))
    missing = [p for p in expected if p not in printed]
    if missing:
        raise SieveError(
            f"sieve {limit}: dropped primes at wheel residue 1: {missing}\n"
            f"  (expected all of {expected})")


@test
def test_wheel_covers_every_coprime_residue():
    """All 48 coprime residues can yield primes, none is unreachable"""
    # A slot lost from the packing shows up as an entire residue class going
    # silent. Every coprime residue mod 210 contains primes (Dirichlet), so a
    # class with zero hits over a wide range means a hole in the table.
    limit = 200000
    coprime = [r for r in range(MODULUS)
               if all(r % p for p in BASE_PRIMES)]
    assert len(coprime) == WHEEL_SLOTS, \
        f"expected {WHEEL_SLOTS} coprime residues, computed {len(coprime)}"

    seen = {p % MODULUS for p in primes_from(limit) if p > 7}
    silent = sorted(set(coprime) - seen)
    if silent:
        raise SieveError(
            f"sieve {limit}: residue classes with no primes at all: {silent}\n"
            f"  every coprime residue mod {MODULUS} should contain primes")


# --------------------------------------------------------------------------
# Properties that must hold of any output
# --------------------------------------------------------------------------

@test
def test_one_is_never_printed():
    """The value 1 is never reported as prime"""
    # 1 occupies a real wheel slot (residue 1, block 0) and is never marked
    # composite, so it is only kept out by an explicit value check.
    for limit in (1, 2, 8, 9, 50, 211, 500, 1000):
        if 1 in primes_from(limit, timeout=10):
            raise SieveError(f"sieve {limit}: printed 1 as a prime")


@test
def test_every_printed_value_is_prime():
    """Trial division confirms each printed value, independently"""
    limit = 20000
    printed = primes_from(limit)
    composites = [n for n in printed if not is_prime_by_trial_division(n)]
    if composites:
        raise SieveError(f"sieve {limit}: these are not prime: {composites[:10]}")


@test
def test_output_is_sorted_and_unique():
    """Output is strictly ascending with no repeats"""
    # Blocks are emitted in order; a bad offset could revisit or reorder one.
    limit = 20000
    printed = primes_from(limit)
    for a, b in zip(printed, printed[1:]):
        if b <= a:
            raise SieveError(f"sieve {limit}: out of order or duplicated "
                             f"at ...{a} {b}...")


@test
def test_exact_list_at_100k():
    """Exact prime list up to 100,000"""
    # Large enough that every sieving prime's 192-step mask pattern wraps many
    # times, which the small-limit tests never reach.
    check_exact(100000)


@test
def test_known_pi_values():
    """Counts match published values of pi(n)"""
    # An external check on the reference sieve itself, so a shared mistake
    # between the two implementations cannot hide.
    known = {10: 4, 100: 25, 1000: 168, 10000: 1229, 100000: 9592}
    for limit, expected in known.items():
        count = len(primes_from(limit))
        if count != expected:
            raise SieveError(f"sieve {limit}: counted {count} primes, "
                             f"pi({limit}) = {expected}")


# --------------------------------------------------------------------------
# Windowed sieving (--from)
# --------------------------------------------------------------------------

@test
def test_reference_window_agrees_with_full_reference():
    """The segmented reference itself is correct"""
    # Guard the guard: a broken reference would make every window test pass.
    for hi in range(0, 260):
        if reference_window(0, hi) != reference_primes(hi):
            raise SieveError(f"reference_window(0, {hi}) disagrees with "
                             f"reference_primes({hi})")


@test
def test_window_boundaries():
    """Windows straddling 210-blocks, word edges and wheel gaps"""
    # A window's first slot is snapped up to a real candidate and its buffer
    # is offset to a word boundary; both are easy to get wrong by one.
    cases = []
    for edge in (0, 210, 420, 2100, 210 * 48):
        for d_lo in (-2, -1, 0, 1, 2):
            for width in (0, 1, 11, 210, 211):
                lo = edge + d_lo
                if lo >= 0:
                    cases.append((lo, lo + width))
    for lo, hi in cases:
        check_window(lo, hi, timeout=10)


@test
def test_window_equals_full_run():
    """Windows agree with the corresponding slice of a full run"""
    full = primes_from(20000)
    for lo, hi in ((0, 20000), (1, 20000), (2, 19999), (7, 11), (8, 10),
                   (100, 200), (4900, 5100), (10000, 20000), (19990, 20000)):
        sliced = [p for p in full if lo <= p <= hi]
        got = window_from(lo, hi, timeout=10)
        if got != sliced:
            raise SieveError(f"sieve --from {lo} {hi}: differs from the full "
                             f"run sliced to the same range "
                             f"({len(got)} vs {len(sliced)} primes)")


@test
def test_window_empty_and_degenerate():
    """Empty, inverted and sub-2 windows produce no primes"""
    for lo, hi in ((10, 5), (0, 0), (0, 1), (1, 1), (24, 28), (114, 126)):
        got = window_from(lo, hi, timeout=10)
        expected = reference_window(lo, hi)
        if got != expected:
            raise SieveError(f"sieve --from {lo} {hi}: got {got}, "
                             f"expected {expected}")


@test
def test_window_far_from_origin():
    """A window far above sqrt(limit), where segmentation actually matters"""
    # The point of --from: sieve near 1e12 without touching everything below.
    for lo, width in ((10**9, 5000), (10**12, 5000), (10**15, 3000)):
        check_window(lo, lo + width, timeout=60)


@test
def test_window_count_matches_listing():
    """--count over a window agrees with listing that window"""
    for lo, hi in ((0, 1000), (1000, 2000), (210, 420), (10**6, 10**6 + 5000)):
        proc = run_sieve("--count", "--from", str(lo), str(hi), timeout=30)
        text = proc.stdout.strip()
        prefix = f"Primes from {lo} to {hi}: "
        if not text.startswith(prefix) or "\n" in text:
            raise SieveError(f"sieve --count --from {lo} {hi}: got {text!r}")
        counted = int(text[len(prefix):])
        listed = len(window_from(lo, hi, timeout=30))
        if counted != listed:
            raise SieveError(f"sieve --count --from {lo} {hi}: reported "
                             f"{counted}, listing gives {listed}")


@test
def test_window_rejects_missing_bound():
    """--from without a number is an error"""
    for flag in ("--from", "-f"):
        proc = run_sieve(flag, timeout=10)
        if proc.returncode == 0:
            raise SieveError(f"sieve {flag}: expected a non-zero exit status")
        if "lower bound" not in proc.stderr:
            raise SieveError(f"sieve {flag}: unhelpful error "
                             f"{proc.stderr.strip()!r}")


@test
def test_large_bounds_parse_without_truncation():
    """Bounds at or above 2^63 survive argument parsing intact"""
    # Regression: the limit was parsed with atol(), which returns a signed
    # long, so anything >= 2^63 saturated at LONG_MAX and the window silently
    # came back empty. An inverted window echoes both bounds and returns at
    # once, so this checks parsing without paying for a base sieve.
    for lo, hi in ((2**64 - 1, 2**63), (2**63 + 12345, 2**63), (10**19, 10)):
        proc = run_sieve("--count", "--from", str(lo), str(hi), timeout=10)
        expected = f"Primes from {lo} to {hi}: 0"
        if proc.stdout.strip() != expected:
            raise SieveError(f"sieve --count --from {lo} {hi}: got "
                             f"{proc.stdout.strip()!r}, expected {expected!r}")


@test
def test_window_at_top_of_range():
    """Windows at 2^63 and just below ULONG_MAX are correct"""
    # Two regressions live here. Parsing must not truncate above 2^63, and the
    # output walk must not advance by value: the next candidate past the last
    # one overflows ULONG_MAX and wraps to a small number, which restarted the
    # walk and emitted tens of millions of bogus "primes".
    ulong_max = 2**64 - 1
    for lo in (2**63, ulong_max - 2000):
        hi = min(lo + 2000, ulong_max)
        got = window_from(lo, hi, timeout=300)
        expected = [n for n in range(lo, hi + 1) if is_prime_miller_rabin(n)]
        if got != expected:
            missing = sorted(set(expected) - set(got))[:5]
            extra = sorted(set(got) - set(expected))[:5]
            raise SieveError(
                f"sieve --from {lo} {hi}: {len(got)} primes, expected "
                f"{len(expected)}\n  missing: {missing}\n  extra: {extra}")


test_window_at_top_of_range.slow = True


@test
def test_window_exhaustive_small():
    """Every window [lo, lo+w] for lo 0..215, w in {0,1,209,210,211}"""
    for lo in range(0, 216):
        for width in (0, 1, 209, 210, 211):
            check_window(lo, lo + width, timeout=10)


test_window_exhaustive_small.slow = True


# --------------------------------------------------------------------------
# Record gap search (--gaps)
# --------------------------------------------------------------------------

# Published terms, taken from the OEIS b-files. The scan below reaches 2e6,
# so these are every term of each sequence up to that point.
OEIS_A002386 = [2, 3, 7, 23, 89, 113, 523, 887, 1129, 1327, 9551, 15683,
                19609, 31397, 155921, 360653, 370261, 492113, 1349533, 1357201]
OEIS_A023186 = [2, 5, 23, 53, 211, 1847, 2179, 3967, 16033, 24281, 38501,
                58831, 203713, 206699, 413353, 1272749]
OEIS_A096265 = [2, 3, 5, 7, 23, 53, 89, 113, 211, 1129, 1327, 2179, 2503,
                5623, 9587, 14107, 19609, 19661, 31397, 31469, 38501, 58831,
                155921, 360749, 370261, 396833, 1357201, 1561919]
OEIS_A058867 = [5, 53, 211, 16787, 69623, 247141]

GAP_LIMIT = 2000000

# The same four sequences, complete to 1e7. A058867 is the reason this range
# is worth the extra time: below 2e6 it agrees with A023186 on the only three
# terms they share, so the range above is where the two sequences actually
# diverge and a filter-of-lonely bug would still pass.
OEIS_1E7 = {
    "gap": [2, 3, 7, 23, 89, 113, 523, 887, 1129, 1327, 9551, 15683, 19609,
            31397, 155921, 360653, 370261, 492113, 1349533, 1357201, 2010733,
            4652353],
    "lonely": [2, 5, 23, 53, 211, 1847, 2179, 3967, 16033, 24281, 38501,
               58831, 203713, 206699, 413353, 1272749, 2198981, 5102953],
    "aloof": [2, 3, 5, 7, 23, 53, 89, 113, 211, 1129, 1327, 2179, 2503, 5623,
              9587, 14107, 19609, 19661, 31397, 31469, 38501, 58831, 155921,
              360749, 370261, 396833, 1357201, 1561919, 4652353, 8917523],
    "equidistant": [5, 53, 211, 16787, 69623, 247141, 3565979, 4911311],
}
OEIS_1E7_NAMES = {"gap": "A002386", "lonely": "A023186",
                  "aloof": "A096265", "equidistant": "A058867"}
GAP_LIMIT_SLOW = 10000000


def read_results(outdir):
    """Read the per-kind results files and the checkpoint file."""
    records = {}
    for kind in ("gap", "lonely", "aloof", "equidistant"):
        rows = []
        path = os.path.join(outdir, f"{kind}.txt")
        if os.path.exists(path):
            for line in open(path):
                if line.startswith("#") or not line.strip():
                    continue
                rows.append(tuple(int(x) for x in line.split()))
        records[kind] = rows
    checkpoints = []
    path = os.path.join(outdir, "progress.txt")
    if os.path.exists(path):
        for line in open(path):
            f = line.split()
            if f and f[0] == "CHECKPOINT":
                checkpoints.append(f[1:])
    return records, checkpoints


def run_gap_search(outdir, limit, extra=()):
    proc = run_sieve("--gaps", "--out", outdir, *extra, str(limit), timeout=120)
    if proc.returncode != 0:
        raise SieveError(f"sieve --gaps ... {limit}: exit {proc.returncode}, "
                         f"stderr={proc.stderr.strip()[:200]!r}")
    return proc


@test
def test_gap_search_reproduces_oeis():
    """--gaps reproduces A002386, A023186, A096265 and A058867 from scratch"""
    with tempfile.TemporaryDirectory() as d:
        prefix = os.path.join(d, "g")
        run_gap_search(prefix, GAP_LIMIT)
        records, checkpoints = read_results(prefix)

        for kind, expected, name in (("gap", OEIS_A002386, "A002386"),
                                     ("lonely", OEIS_A023186, "A023186"),
                                     ("aloof", OEIS_A096265, "A096265"),
                                     ("equidistant", OEIS_A058867,
                                      "A058867")):
            got = [r[1] for r in records[kind]]   # column 2 is the prime
            if got != expected:
                for i, (a, b) in enumerate(zip(got, expected)):
                    if a != b:
                        raise SieveError(f"{kind} ({name}) differs at term "
                                         f"{i+1}: got {a}, OEIS has {b}")
                raise SieveError(f"{kind} ({name}): found {len(got)} terms, "
                                 f"OEIS has {len(expected)} below {GAP_LIMIT}")
        if not checkpoints:
            raise SieveError("no CHECKPOINT line was written")


@test
def test_gap_search_reproduces_oeis_to_ten_million():
    """--gaps reproduces all four sequences from zero to 1e7"""
    # 2e6 is not far enough to be convincing about A058867: below it, the
    # only balanced primes that set a record are the three A023186 also has,
    # so a "filter the lonely records" implementation would pass. 3565979 and
    # 4911311 are the first two terms where the two sequences part company.
    with tempfile.TemporaryDirectory() as d:
        prefix = os.path.join(d, "g")
        run_gap_search(prefix, GAP_LIMIT_SLOW)
        records, _ = read_results(prefix)

        for kind, expected in OEIS_1E7.items():
            name = OEIS_1E7_NAMES[kind]
            got = [r[1] for r in records[kind]]
            if got == expected:
                continue
            for i, (x, y) in enumerate(zip(got, expected)):
                if x != y:
                    raise SieveError(f"{kind} ({name}) differs at term "
                                     f"{i+1}: got {x}, OEIS has {y}")
            raise SieveError(f"{kind} ({name}): found {len(got)} terms, "
                             f"OEIS has {len(expected)} below "
                             f"{GAP_LIMIT_SLOW}")


test_gap_search_reproduces_oeis_to_ten_million.slow = True


@test
def test_gap_search_resume_is_lossless():
    """A killed and resumed search yields the same records as one pass"""
    # The whole point of the results file: stopping must not lose or
    # duplicate a record, and must not shift the thresholds.
    with tempfile.TemporaryDirectory() as d:
        whole = os.path.join(d, "whole")
        run_gap_search(whole, GAP_LIMIT)

        staged = os.path.join(d, "staged")
        for stop in (700000, 1300000, GAP_LIMIT):
            run_gap_search(staged, stop)

        a, _ = read_results(whole)
        b, _ = read_results(staged)
        for kind in ("gap", "lonely", "aloof", "equidistant"):
            if a[kind] != b[kind]:
                raise SieveError(f"{kind}: resumed run differs from one pass\n"
                                 f"  one pass: {a[kind][:6]}\n"
                                 f"  resumed : {b[kind][:6]}")


@test
def test_gap_search_checkpoint_round_trips():
    """A checkpoint carries enough state to continue exactly"""
    with tempfile.TemporaryDirectory() as d:
        prefix = os.path.join(d, "g")
        run_gap_search(prefix, 500000)
        _, checkpoints = read_results(prefix)
        if not checkpoints:
            raise SieveError("no checkpoint written")

        last = checkpoints[-1]
        if len(last) < 4:
            raise SieveError(f"checkpoint has {len(last)} fields, expected >=4: "
                             f"{last}")
        p_prev, p_last = int(last[0]), int(last[1])
        if not (p_prev < p_last):
            raise SieveError(f"checkpoint primes out of order: {p_prev}, {p_last}")
        for p in (p_prev, p_last):
            if not is_prime_miller_rabin(p):
                raise SieveError(f"checkpoint holds a non-prime: {p}")


@test
def test_gap_results_files_are_separate():
    """Each sequence gets its own results file in the output directory"""
    # Results files hold only results, so they stay directly comparable to an
    # OEIS b-file; restart state lives apart from them.
    with tempfile.TemporaryDirectory() as d:
        prefix = os.path.join(d, "g")
        run_gap_search(prefix, 500000)
        if not os.path.isdir(prefix):
            raise SieveError("--out did not create the output directory")
        for kind in ("gap", "lonely", "aloof", "progress"):
            path = os.path.join(prefix, f"{kind}.txt")
            if not os.path.exists(path):
                raise SieveError(f"missing output file {kind}.txt")
        for kind in ("gap", "lonely", "aloof"):
            for line in open(os.path.join(prefix, f"{kind}.txt")):
                if line.startswith("#") or not line.strip():
                    continue
                if len(line.split()) != 7:
                    raise SieveError(f"{kind}: malformed results line {line!r}")
                if "CHECKPOINT" in line:
                    raise SieveError(f"{kind}: checkpoint leaked into results")


@test
def test_gap_records_carry_verifiable_neighbours():
    """Every record line holds a genuine prime triple"""
    # The neighbour columns exist so a line can be checked on its own; verify
    # they really are the adjacent primes, independently of the sieve.
    with tempfile.TemporaryDirectory() as d:
        prefix = os.path.join(d, "g")
        run_gap_search(prefix, 200000)
        records, _ = read_results(prefix)
        checked = 0
        for kind in ("gap", "lonely", "aloof"):
            for n, p, value, below, above, prev, nxt in records[kind]:
                if prev == 0:
                    continue                      # p = 2 has no lower neighbour
                for q in (prev, p, nxt):
                    if not is_prime_miller_rabin(q):
                        raise SieveError(f"{kind} #{n}: {q} is not prime")
                if p - prev != below or nxt - p != above:
                    raise SieveError(f"{kind} #{n}: neighbours {prev},{nxt} "
                                     f"disagree with gaps {below},{above}")
                for q in range(prev + 1, p):
                    if is_prime_miller_rabin(q):
                        raise SieveError(f"{kind} #{n}: {q} lies between "
                                         f"{prev} and {p}")
                checked += 1
        if checked < 20:
            raise SieveError(f"only {checked} records checked -- too few")


@test
def test_gap_search_requires_out_file():
    """--gaps without --out is an error"""
    proc = run_sieve("--gaps", "1000", timeout=10)
    if proc.returncode == 0:
        raise SieveError("sieve --gaps without --out: expected non-zero exit")
    if "--out" not in proc.stderr:
        raise SieveError(f"unhelpful error: {proc.stderr.strip()!r}")


@test
def test_gap_exit_code_reports_completion():
    """Exit status distinguishes finishing the range from being interrupted"""
    # pgaps.py relies on this to know a worker actually covered its range;
    # a checkpoint alone cannot say, since it names the last prime seen.
    with tempfile.TemporaryDirectory() as d:
        proc = run_sieve("--gaps", "--out", os.path.join(d, "done"),
                         "200000", timeout=60)
        if proc.returncode != 0:
            raise SieveError(f"completed run exited {proc.returncode}, expected 0")

        p = subprocess.Popen([BINARY, "--gaps", "--out", os.path.join(d, "cut"),
                              "400000000000"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        p.terminate()
        rc = p.wait(timeout=60)
        if rc != 2:
            raise SieveError(f"interrupted run exited {rc}, expected 2")


@test
def test_gap_out_creates_nested_directories():
    """--out creates missing parent directories"""
    with tempfile.TemporaryDirectory() as d:
        nested = os.path.join(d, "a", "b", "c")
        run_gap_search(nested, 100000)
        for kind in ("gap", "lonely", "aloof", "progress"):
            if not os.path.exists(os.path.join(nested, f"{kind}.txt")):
                raise SieveError(f"missing {kind}.txt under a nested --out")


@test
def test_parallel_merge_matches_serial():
    """A sharded run merges to exactly the serial result"""
    # The whole correctness claim for pgaps.py: workers emit candidates
    # against a shared threshold, and the merge applies the running maximum.
    driver = os.path.join(HERE, "pgaps.py")
    if not os.path.exists(driver):
        raise SieveError("pgaps.py is missing")

    with tempfile.TemporaryDirectory() as d:
        serial = os.path.join(d, "serial")
        run_gap_search(serial, 3000000)

        par = os.path.join(d, "par")
        proc = subprocess.run([sys.executable, driver, "--from", "0",
                               "--to", "3000000", "--jobs", "4", "--out", par],
                              capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise SieveError(f"pgaps.py exited {proc.returncode}: "
                             f"{proc.stdout[-400:]}{proc.stderr[-400:]}")

        a, _ = read_results(serial)
        b, _ = read_results(par)
        for kind in ("gap", "lonely", "aloof", "equidistant"):
            sa = [r[1:] for r in a[kind]]
            sb = [r[1:] for r in b[kind]]
            if sa != sb:
                raise SieveError(
                    f"{kind}: parallel merge differs from serial\n"
                    f"  serial   {len(sa)} records, first diff around "
                    f"{[x for x, y in zip(sa, sb) if x != y][:2]}\n"
                    f"  parallel {len(sb)} records")
        if not b["aloof"]:
            raise SieveError("parallel run produced no records -- vacuous test")


test_parallel_merge_matches_serial.slow = True


# --------------------------------------------------------------------------
# --count mode
# --------------------------------------------------------------------------

@test
def test_count_matches_printed_list():
    """--count agrees with the number of primes actually listed"""
    # --count walks the same bitset but skips printf, so the two paths can
    # drift apart. Cover both output paths, including the limit < 8 shortcut.
    for limit in (0, 1, 2, 7, 8, 9, 50, 121, 209, 210, 211, 500, 1000, 20011):
        counted = count_from(limit, "--count", timeout=10)
        listed = len(primes_from(limit, timeout=10))
        if counted != listed:
            raise SieveError(f"sieve --count {limit}: reported {counted}, "
                             f"but listing the primes yields {listed}")


@test
def test_count_matches_reference():
    """--count agrees with the reference sieve"""
    for limit in (100, 1000, 10000, 100000):
        counted = count_from(limit, "--count")
        expected = len(reference_primes(limit))
        if counted != expected:
            raise SieveError(f"sieve --count {limit}: reported {counted}, "
                             f"expected {expected}")


@test
def test_count_short_flag_and_argument_order():
    """-c is accepted, and the flag may come before or after the limit"""
    expected = len(reference_primes(1000))
    for flags, limit in ((("--count",), 1000), (("-c",), 1000)):
        if count_from(limit, *flags) != expected:
            raise SieveError(f"sieve {flags[0]} {limit}: wrong total")

    # Flag after the limit.
    proc = run_sieve("1000", "--count", timeout=10)
    if proc.stdout.strip() != f"Primes up to 1000: {expected}":
        raise SieveError(f"sieve 1000 --count: got {proc.stdout.strip()!r}")


@test
def test_count_prints_no_primes():
    """--count emits one line only, never the prime list"""
    proc = run_sieve("--count", "1000", timeout=10)
    lines = proc.stdout.strip().split("\n")
    if len(lines) != 1:
        raise SieveError(f"sieve --count 1000: expected 1 line of output, "
                         f"got {len(lines)}")


@test
def test_repeat_does_not_change_output():
    """--repeat runs the sieve N times but reports exactly once"""
    # --repeat exists for benchmarking; extra passes must be invisible.
    for limit in (50, 1000, 20011):
        once = run_sieve(str(limit), timeout=30).stdout
        many = run_sieve("--repeat", "4", str(limit), timeout=30).stdout
        if once != many:
            raise SieveError(f"sieve --repeat 4 {limit}: output differs from a "
                             f"single pass")
        if count_from(limit, "--count", "--repeat", "3", timeout=30) != \
                count_from(limit, "--count", timeout=30):
            raise SieveError(f"sieve --count --repeat 3 {limit}: count differs")


@test
def test_repeat_rejects_missing_count():
    """--repeat without a number is an error, not a silent default"""
    # The bare flag must not let the next argument be eaten as the limit.
    for flag in ("--repeat", "-r"):
        proc = run_sieve(flag, timeout=10)
        if proc.returncode == 0:
            raise SieveError(f"sieve {flag}: expected a non-zero exit status")
        if "repeat count" not in proc.stderr:
            raise SieveError(f"sieve {flag}: unhelpful error {proc.stderr.strip()!r}")


# --------------------------------------------------------------------------
# Command line behaviour
# --------------------------------------------------------------------------

@test
def test_default_limit_is_500():
    """Running with no arguments sieves to 500"""
    proc = run_sieve()
    if proc.returncode != 0:
        raise SieveError(f"sieve (no args): exit status {proc.returncode}")
    lines = proc.stdout.strip().split("\n")
    if lines[0] != f"Primes up to {DEFAULT_LIMIT}:":
        raise SieveError(f"sieve (no args): header was {lines[0]!r}")
    printed = [int(t) for t in " ".join(lines[1:]).split()]
    if printed != reference_primes(DEFAULT_LIMIT):
        raise SieveError("sieve (no args): output differs from reference "
                         f"for limit {DEFAULT_LIMIT}")


@test
def test_help_flags():
    """--help and -h print usage and exit 0"""
    for flag in ("--help", "-h"):
        proc = run_sieve(flag, timeout=10)
        if proc.returncode != 0:
            raise SieveError(f"sieve {flag}: exit status {proc.returncode}, "
                             f"expected 0")
        text = proc.stdout + proc.stderr
        if "Usage:" not in text:
            raise SieveError(f"sieve {flag}: no usage text in output")
        for documented in ("--count", "--repeat", "--from", "--gaps",
                           "--out", "<limit>"):
            if documented not in text:
                raise SieveError(f"sieve {flag}: {documented} is undocumented")


@test
def test_non_numeric_arguments_are_ignored():
    """Unrecognised arguments fall back to the default limit"""
    # parse_args() documents this as graceful, so pin the behaviour down.
    for arg in ("--verbose", "abc", "-x"):
        proc = run_sieve(arg, timeout=10)
        if proc.returncode != 0:
            raise SieveError(f"sieve {arg}: exit status {proc.returncode}")
        if not proc.stdout.startswith(f"Primes up to {DEFAULT_LIMIT}:"):
            raise SieveError(f"sieve {arg}: did not fall back to the default "
                             f"limit, got {proc.stdout.splitlines()[0]!r}")


@test
def test_last_argument_wins():
    """With several numeric arguments the last one is used"""
    proc = run_sieve("100", "50", timeout=10)
    if not proc.stdout.startswith("Primes up to 50:"):
        raise SieveError("sieve 100 50: expected the last limit to win, got "
                         f"{proc.stdout.splitlines()[0]!r}")


# --------------------------------------------------------------------------
# Larger ranges (opt in with --slow)
# --------------------------------------------------------------------------

@test
def test_one_million_exact():
    """Exact prime list up to 1,000,000"""
    check_exact(1000000)


test_one_million_exact.slow = True


@test
def test_ten_million_count():
    """pi(10,000,000) == 664579"""
    count = count_from(10000000, "--count", timeout=300)
    if count != 664579:
        raise SieveError(f"sieve 10000000: counted {count}, expected 664579")


test_ten_million_count.slow = True


# --------------------------------------------------------------------------

def build():
    """Compile the binary via make, so tests always run against fresh code."""
    proc = subprocess.run(["make", "--silent", "sieve"], cwd=HERE,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        print("Build failed:\n" + proc.stdout + proc.stderr, file=sys.stderr)
        sys.exit(1)
    warnings = proc.stderr.strip()
    if warnings:
        print("Compiler warnings:\n" + warnings + "\n", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="print each test as it runs")
    parser.add_argument("--slow", action="store_true",
                        help="also run the 1e6 and 1e7 range checks")
    parser.add_argument("--binary", metavar="PATH",
                        help="test an already-built binary instead of ./sieve "
                             "(used by 'make test-widths')")
    args = parser.parse_args()

    if args.binary:
        global BINARY
        BINARY = os.path.abspath(args.binary)
        if not os.path.exists(BINARY):
            sys.exit(f"no such binary: {BINARY}")
    else:
        build()

    selected = [t for t in TESTS if args.slow or not getattr(t, "slow", False)]
    skipped = len(TESTS) - len(selected)

    failures = []
    for fn in selected:
        name = (fn.__doc__ or fn.__name__).strip()
        if args.verbose:
            print(f"  {name} ... ", end="", flush=True)
        try:
            fn()
        except AssertionError as exc:
            failures.append((name, str(exc)))
            print("FAIL" if args.verbose else "F", end="", flush=True)
        else:
            print("ok" if args.verbose else ".", end="", flush=True)
        if args.verbose:
            print()

    if not args.verbose:
        print()

    for name, message in failures:
        print(f"\nFAIL: {name}\n{message}")

    passed = len(selected) - len(failures)
    print(f"\n{passed}/{len(selected)} tests passed"
          + (f", {len(failures)} failed" if failures else "")
          + (f" ({skipped} slow tests skipped, use --slow)" if skipped else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
