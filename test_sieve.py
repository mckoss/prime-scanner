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

HERE = os.path.dirname(os.path.abspath(__file__))
BINARY = os.path.join(HERE, "sieve")

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
        for documented in ("--count", "--repeat", "<limit>"):
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
    args = parser.parse_args()

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
