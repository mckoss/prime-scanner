#!/usr/bin/env python3
"""Parallel driver for ./sieve --gaps.

Splits a range across N worker processes, then merges their output into a
single set of results.

The merge is not optional bookkeeping -- it is what makes the answer correct.
A record is a running maximum over the whole scan, so a worker covering
[1e13, 2e13] cannot know whether its local best beats everything below it.
Each worker therefore emits *candidates*: primes whose value exceeds the
threshold in force when the search began. No true record can be missed that
way (a record must beat that threshold too), and the serial merge pass then
applies the running-maximum rule in order to select the real ones.

Workers overlap slightly at their lower edge so the 3-prime sliding window is
primed before the range they are responsible for; the duplicate candidates
that produces are removed by the merge.

Usage:
    python3 pgaps.py --to 1e13 --jobs 8 --out verify          # from scratch
    python3 pgaps.py --from 2e12 --to 1e13 --jobs 8 --out run --seed results
    python3 pgaps.py --out run --merge-only
"""

import argparse
import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BINARY = os.path.join(HERE, "sieve")
KINDS = ("gap", "lonely", "aloof", "equidistant")

# balanced.txt is deliberately not here: it is filtered out of the merged
# lonely records afterwards, and the sieve never emits a candidate for it.
# See derive_balanced(). "equidistant" IS here and is not the same thing --
# it is a running maximum the sieve keeps, over the balanced primes alone.

# Enough to prime a worker's 3-prime window before its own range begins.
# The largest known prime gap below 1e20 is 1854, so this is ample; it is
# capped against the shard span so small ranges still parallelise.
OVERLAP = 100_000


def read_records(path):
    """Rows of <n> <prime> <value> <below> <above> <prev> <next>."""
    rows = []
    if os.path.exists(path):
        for line in open(path):
            if line.startswith("#") or not line.strip():
                continue
            f = line.split()
            if len(f) == 7:
                rows.append(tuple(int(x) for x in f))
    return rows


def write_records(path, rows, header):
    with open(path, "w") as f:
        f.write(header)
        for i, r in enumerate(rows, 1):
            f.write(" ".join(str(x) for x in (i,) + tuple(r[1:])) + "\n")


def read_coverage(out):
    """How far each kind has been scanned from zero.

    Kinds can be at different points. Adding a kind to KINDS puts it at 0
    while the others stay where they are, and the driver catches it up before
    scanning any further -- which is the whole reason this file exists.

    A run from before coverage.txt was written has none, so it is inferred:
    whatever it scanned, it scanned for every kind it knew about, so a kind
    with a records file is covered to the frontier and a kind without one has
    never been scanned. That is exactly the state a newly added kind is in.
    """
    cov = {k: 0 for k in KINDS}
    path = os.path.join(out, "coverage.txt")
    if os.path.exists(path):
        for line in open(path):
            if line.startswith("#") or not line.strip():
                continue
            f = line.split()
            if len(f) >= 2 and f[0] in cov:
                cov[f[0]] = int(f[1])
        return cov

    front = 0
    fpath = os.path.join(out, "frontier.txt")
    if os.path.exists(fpath):
        front = int(open(fpath).read().split()[0])
    for k in KINDS:
        if os.path.exists(os.path.join(out, f"{k}.txt")):
            cov[k] = front
    return cov


def write_coverage(out, cov):
    with open(os.path.join(out, "coverage.txt"), "w") as f:
        f.write("# how far each kind is scanned from zero, which is not always\n"
                "# the same point: <kind> <covered_to>\n")
        for k in KINDS:
            f.write(f"{k} {cov.get(k, 0)}\n")


def read_round(path):
    """The round in flight: (lo, hi, jobs, kinds)."""
    f = open(path).read().split()
    kinds = tuple(f[3].split(",")) if len(f) > 3 else KINDS
    return int(f[0]), int(f[1]), int(f[2]), kinds


def write_round(path, lo, hi, jobs, kinds):
    open(path, "w").write(f"{lo} {hi} {jobs} {','.join(kinds)}\n")


def derive_balanced(out):
    """Lonely records whose two neighbours are equidistant.

    A023186 terms that are also balanced primes (A006562). This is a *filter*
    on the merged lonely records, not a record sequence of its own, so the
    workers collect nothing for it and it needs no threshold: a balanced
    lonely prime is by definition already a lonely record, so lonely.txt
    holds every term there can be below the frontier.

    p = 2 is excluded. It has no lower neighbour, so it is not balanced.
    """
    rows = [r for r in read_records(os.path.join(out, "lonely.txt"))
            if r[5] and r[3] == r[4]]
    write_records(os.path.join(out, "balanced.txt"), rows,
                  "# balanced-lonely records: <n> <prime> <value> <gap_below> "
                  "<gap_above> <prev_prime> <next_prime>\n"
                  "# lonely.txt filtered to gap_below == gap_above; a subset "
                  "of the lonely records, not a record sequence of its own\n")
    return rows


def seed_from(directory):
    """Highest published/known record per kind, to seed every worker."""
    seed = {}
    for kind in KINDS:
        rows = read_records(os.path.join(directory, f"{kind}.txt")) if directory else []
        seed[kind] = max(rows, key=lambda r: r[2]) if rows else None
    return seed


class Stopping(Exception):
    """Raised when a signal asks the run to wind down."""


def install_signal_handlers():
    """Treat SIGTERM and SIGHUP like Ctrl-C.

    Only SIGINT arrived as KeyboardInterrupt, so `timeout`, `kill` or closing
    the terminal killed the driver outright and left its workers running.
    Orphaned workers keep writing to the shard directories, and a second
    driver started on the same output then desyncs the done-markers from the
    merge -- which silently loses records.
    """
    def handler(signum, frame):
        raise KeyboardInterrupt
    for sig in (signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(sig, handler)
        except (ValueError, OSError):
            pass


def acquire_lock(out):
    """Refuse to run two drivers against the same output directory."""
    path = os.path.join(out, "lock")
    if os.path.exists(path):
        try:
            pid = int(open(path).read().split()[0])
            os.kill(pid, 0)                       # raises if not running
        except (ValueError, IndexError, ProcessLookupError, PermissionError):
            pass                                  # stale lock, take it
        else:
            sys.exit(f"another pgaps.py (pid {pid}) is already using {out}\n"
                     f"stop it first, or remove {path} if it is stale")
    open(path, "w").write(f"{os.getpid()}\n")
    return path


def kill_workers(procs):
    for _, p, _ in procs:
        if p.poll() is None:
            try:
                p.terminate()
            except ProcessLookupError:
                pass
    for _, p, _ in procs:
        try:
            p.wait(timeout=60)
        except Exception:
            try:
                p.kill()
            except ProcessLookupError:
                pass


def shard_dir(out, i):
    return os.path.join(out, "shards", f"{i:03d}")


# Measured scan rate (log10 x -> numbers/sec) on an M1 Max. Used only to
# balance the shards; being a little off costs load balance, not correctness.
RATE_POINTS = [(12, 1.071e9), (13, 9.643e8), (14, 7.463e8),
               (15, 5.168e8), (16, 3.256e8)]


def scan_rate(x):
    import math
    lx = [p[0] for p in RATE_POINTS]
    lr = [math.log10(p[1]) for p in RATE_POINTS]
    L = math.log10(max(x, 1e6))
    if L <= lx[0]:
        return 10 ** lr[0]
    if L >= lx[-1]:
        slope = (lr[-1] - lr[-2]) / (lx[-1] - lx[-2])
        return 10 ** (lr[-1] + slope * (L - lx[-1]))
    for i in range(1, len(lx)):
        if L < lx[i]:
            t = (L - lx[i - 1]) / (lx[i] - lx[i - 1])
            return 10 ** (lr[i - 1] + t * (lr[i] - lr[i - 1]))
    return 10 ** lr[-1]


def split_by_time(lo, hi, jobs, steps=20000):
    """Equal-time shards, not equal-length ones.

    Throughput falls as the magnitude rises, so equal-length shards finish at
    very different times and the run waits on the topmost one. Splitting on
    estimated cost keeps every worker busy for about the same span.
    """
    edges, acc, prev = [lo], 0.0, lo
    costs = []
    for k in range(1, steps + 1):
        x = lo + (hi - lo) * k / steps
        costs.append((x, (x - prev) / scan_rate((x + prev) / 2)))
        prev = x
    total = sum(c for _, c in costs)
    target = total / jobs
    for x, c in costs:
        acc += c
        if acc >= target and len(edges) < jobs:
            edges.append(int(x))
            acc = 0.0
    edges.append(hi)
    return [(edges[i], edges[i + 1]) for i in range(jobs)]


def prepare(out, jobs, lo, hi, seed):
    """Create and seed the worker directories. Returns their ranges."""
    ranges = split_by_time(lo, hi, jobs)
    for i, (a, b) in enumerate(ranges):
        d = shard_dir(out, i)
        os.makedirs(d, exist_ok=True)
        # Only seed a worker that has not already started; otherwise its own
        # results carry the thresholds and its progress.txt the position.
        if not os.path.exists(os.path.join(d, "progress.txt")):
            for kind in KINDS:
                row = seed.get(kind)
                with open(os.path.join(d, f"{kind}.txt"), "w") as f:
                    f.write(f"# {kind} candidates for shard {i} "
                            f"[{a}, {b}) -- merge before use\n")
                    if row:
                        f.write(" ".join(str(x) for x in row) + "\n")
    return ranges


def launch(out, ranges, checkpoint, ids=None):
    procs = []
    ids = ids if ids is not None else list(range(len(ranges)))
    for i, (a, b) in zip(ids, ranges):
        d = shard_dir(out, i)
        span = b - a
        start = max(a - min(OVERLAP, max(span // 4, 1000)), 2)
        log = open(os.path.join(d, "log.txt"), "a")
        p = subprocess.Popen(
            [BINARY, "--gaps", "--from", str(start), "--out", d,
             "--checkpoint", str(checkpoint), str(b)],
            stdout=subprocess.DEVNULL, stderr=log)
        procs.append((i, p, log))
    return procs


def mark_done(out, i):
    open(os.path.join(shard_dir(out, i), "done.txt"), "w").write("complete\n")


def is_done(out, i):
    return os.path.exists(os.path.join(shard_dir(out, i), "done.txt"))


def position_of(out, i):
    path = os.path.join(shard_dir(out, i), "progress.txt")
    last = None
    if os.path.exists(path):
        for line in open(path):
            if line.startswith("CHECKPOINT"):
                last = line.split()
    return int(last[2]) if last else None


def monitor(out, procs, ranges, interval=15):
    started = time.time()
    try:
        while any(p.poll() is None for _, p, _ in procs):
            time.sleep(interval)
            for i, p, _ in procs:
                rc = p.poll()
                if rc == 0 and not is_done(out, i):
                    mark_done(out, i)
            done = sum(1 for _, p, _ in procs if p.poll() is not None)
            scanned = 0
            for i, (a, b) in enumerate(ranges):
                if is_done(out, i):
                    scanned += b - a
                    continue
                pos = position_of(out, i)
                if pos:
                    scanned += max(0, min(pos, b) - a)
            total = ranges[-1][1] - ranges[0][0]
            el = time.time() - started
            print(f"  [{el:7.0f}s] {done}/{len(procs)} workers done  "
                  f"{100.0 * scanned / total:5.1f}% of range  "
                  f"{scanned / max(el, 1e-9):.2e} nums/s aggregate", flush=True)
    except KeyboardInterrupt:
        print("\n  interrupted -- signalling workers to checkpoint", flush=True)
        kill_workers(procs)
        return False
    return True


def safe_frontier(out, ranges):
    """Highest point below which coverage is provably contiguous.

    A worker stopped mid-shard leaves a hole, and merging across a hole can
    promote a later, smaller value to "record" when the real one sits in the
    gap. So results are only final below the lowest point any worker has
    reached.
    """
    front = ranges[0][0]
    for i, (a, b) in enumerate(ranges):
        if is_done(out, i):
            front = b                      # this shard is fully covered
            continue
        # First incomplete shard: coverage ends where it has reached, and
        # nothing beyond it counts even if later shards ran ahead.
        return max(front, position_of(out, i) or a)
    return front


def merge(out, lo, seed, upto=None, kinds=KINDS):
    """Apply the running-maximum rule across every worker's candidates.

    Incremental: records already in <out> are kept and act as the threshold,
    so rounds can be merged one after another.

    `kinds` narrows it to a subset. A catch-up round scans a range the other
    kinds have already covered, so merging their candidates would be at best
    a no-op and at worst a way to disturb a finished file; only the kinds
    being caught up are written.
    """
    os.makedirs(out, exist_ok=True)
    summary = {}
    shards = sorted(os.listdir(os.path.join(out, "shards")))
    for kind in kinds:
        cands = read_records(os.path.join(out, f"{kind}.txt"))
        emitted = False
        for d in shards:
            path = os.path.join(out, "shards", d, f"{kind}.txt")
            emitted = emitted or os.path.exists(path)
            cands += read_records(path)
        # A sieve older than this driver knows nothing about a kind added
        # since, and writes no file for it. Merging that silently produces an
        # EMPTY records file and then marks it covered -- a false completeness
        # claim, which is the one failure this whole scan exists to avoid.
        if shards and not emitted:
            sys.exit(f"no worker produced {kind}.txt: ./sieve does not know "
                     f"that record kind.\nIt is older than this driver -- "
                     f"run 'make' and start again.")
        if upto is not None:
            cands = [r for r in cands if r[1] <= upto]

        # Drop the seed rows (they sit below the search start) and dedupe the
        # overlap regions, where two workers see the same centre prime.
        seen, uniq = set(), []
        for r in sorted(cands, key=lambda r: r[1]):
            if lo is not None and r[1] < lo:
                continue
            if r[1] in seen:
                continue
            seen.add(r[1])
            uniq.append(r)

        best = seed[kind][2] if seed.get(kind) else 0
        kept = [seed[kind]] if seed.get(kind) else []
        if kept and uniq and uniq[0][1] <= kept[0][1]:
            kept = []           # the seed row is already among the candidates
        for r in uniq:
            if r[2] > best:
                best = r[2]
                kept.append(r)

        write_records(os.path.join(out, f"{kind}.txt"), kept,
                      f"# {kind} records: <n> <prime> <value> <gap_below> "
                      f"<gap_above> <prev_prime> <next_prime>\n"
                      f"# merged from {len(cands)} candidates across "
                      f"{len(os.listdir(os.path.join(out, 'shards')))} workers\n")
        summary[kind] = (len(cands), len(kept), best)

    # Its "candidates" are the lonely records it filters, so it reports in
    # the same shape as the scanned kinds. Nothing to redo if lonely was not
    # part of this merge.
    if "lonely" in kinds:
        bal = derive_balanced(out)
        summary["balanced"] = (summary["lonely"][1], len(bal),
                               bal[-1][2] if bal else 0)
    return summary


def verify_coverage(out, ranges):
    """Every worker must have run its range to completion.

    Completion is recorded by a marker written only when the worker exits 0.
    Position alone will not do: a worker's last checkpoint names the last
    prime it saw, which is legitimately a little below the range end.
    """
    holes = []
    for i, (a, b) in enumerate(ranges):
        if not is_done(out, i):
            holes.append((i, a, b, position_of(out, i)))
    return holes


def run_round(out, lo, hi, jobs, seed, checkpoint):
    """Scan [lo, hi) across `jobs` workers. Returns (finished, frontier)."""
    ranges = prepare(out, jobs, lo, hi, seed)
    pending = [(i, r) for i, r in enumerate(ranges) if not is_done(out, i)]
    if pending:
        if len(pending) < len(ranges):
            print(f"    {len(ranges) - len(pending)} worker(s) already complete")
        procs = launch(out, [r for _, r in pending], checkpoint,
                       [i for i, _ in pending])
        try:
            finished = monitor(out, procs, ranges)
        finally:
            # Whatever happens to the driver, its workers go with it.
            kill_workers(procs)
            for i, p, log in procs:
                if p.poll() == 0:
                    mark_done(out, i)
                log.close()
    else:
        finished = True
    return finished, safe_frontier(out, ranges), ranges


def clear_shards(out):
    import shutil
    d = os.path.join(out, "shards")
    if os.path.isdir(d):
        shutil.rmtree(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="lo", type=float, default=0,
                    help="range start (default 0, i.e. derive every record "
                         "from scratch)")
    ap.add_argument("--to", dest="hi", type=float,
                    help="range end. Omit to run open-ended in rolling rounds "
                         "until interrupted, like ./sieve --gaps")
    ap.add_argument("--round-seconds", type=int, default=600,
                    help="target wall time per round when --to is omitted "
                         "(default 600); each round ends in a merge")
    ap.add_argument("--jobs", "-j", type=int, default=os.cpu_count() or 4,
                    help="worker processes (default: all cores). Prefer the "
                         "number of FREE performance cores; efficiency cores "
                         "add little and a busy core costs more than it gives")
    ap.add_argument("--out", required=True,
                    help="output directory; merged results land here and "
                         "workers under <out>/shards/")
    ap.add_argument("--seed", help="results directory supplying start thresholds")
    ap.add_argument("--checkpoint", type=int, default=30,
                    help="seconds between each worker's checkpoints (default 30)")
    ap.add_argument("--merge-only", action="store_true",
                    help="re-merge existing worker output without scanning")
    ap.add_argument("--status", action="store_true",
                    help="print how far each kind is covered, and exit")
    args = ap.parse_args()

    if not os.path.exists(BINARY):
        sys.exit("./sieve not built -- run 'make' first")

    os.makedirs(args.out, exist_ok=True)
    install_signal_handlers()
    globals()["_LOCK_PATH"] = acquire_lock(args.out)
    seed = seed_from(args.seed)
    state = os.path.join(args.out, "round.txt")

    cov = read_coverage(args.out)

    if args.status:
        target = max(cov.values())
        print(f"  {args.out}/")
        for kind in KINDS:
            n = len(read_records(os.path.join(args.out, f"{kind}.txt")))
            flag = "" if cov[kind] >= target else "   <-- BEHIND, will catch up"
            print(f"    {kind:<12} {n:>3} records   covered to "
                  f"{cov[kind]:,}{flag}")
        print(f"  resumes at {target:,}")
        print(f"  frontier   {min(cov.values()):,}  "
              f"(complete for every sequence below this)")
        return 0

    if args.merge_only:
        if not os.path.exists(state):
            sys.exit(f"{state} missing -- nothing to merge")
        lo, hi, jobs, kinds = read_round(state)
        ranges = prepare(args.out, jobs, lo, hi, seed)
        front = safe_frontier(args.out, ranges)
        summary = merge(args.out, None, seed, upto=front, kinds=kinds)
        for kind, (n, k, best) in summary.items():
            print(f"    {kind:<12} {n:>5} candidates -> {k:>3} records   best {best}")
        return 0

    # An unfinished round takes precedence: resume it before advancing.
    resume = None
    if os.path.exists(state):
        a, b, j, kinds = read_round(state)
        ranges = prepare(args.out, j, a, b, seed)
        if any(not is_done(args.out, i) for i in range(j)):
            resume = (a, b, j, kinds)

    # Where the run RESUMES is the furthest any kind has reached. That is not
    # the same as the frontier it can claim, which is the point every kind has
    # reached -- the two differ exactly while a catch-up is pending.
    frontier_file = os.path.join(args.out, "frontier.txt")
    lo = max(int(args.lo), max(cov.values()))

    # A kind added after the run started sits at 0 while the rest are at the
    # frontier. Catch it up over the range they have already covered, on its
    # own, before advancing any further.
    behind = [k for k in KINDS if cov[k] < max(cov.values())]
    if behind and not resume:
        print(f"  catching up {', '.join(behind)}: covered to "
              f"{min(cov[k] for k in behind):,}, the rest to "
              f"{max(cov.values()):,}")
        print(f"  the other kinds are left untouched until it is level")

    bounded = args.hi is not None
    hi_final = int(args.hi) if bounded else None
    if bounded and lo >= hi_final and not behind:
        print("  nothing to do: frontier is already at or past --to")
        return 0

    if resume:
        where = f"resuming round [{resume[0]:,}, {resume[1]:,})"
    elif behind:
        where = f"catching up from {min(cov[k] for k in behind):,}"
    elif bounded:
        where = f"scanning [{lo:,}, {hi_final:,})"
    else:
        where = f"scanning from {lo:,}, open-ended"
    print(f"  {where} across {args.jobs} workers")
    for kind in KINDS:
        row = seed.get(kind)
        print(f"    {kind:<12} seed threshold {row[2] if row else 0}")

    while True:
        if resume:
            a, b, jobs, kinds = resume
            resume = None
            # A round that started before a kind was added scanned nothing for
            # it below the round's own start, so its candidates must not be
            # merged as if they covered the range from zero. Drop it here; the
            # catch-up in the next round picks it up properly. A round that IS
            # a catch-up names its own kinds and is left alone.
            if set(kinds) == set(KINDS):
                level = max(cov.values())
                kinds = tuple(k for k in KINDS if cov[k] >= level)
            print(f"\n  resuming round [{a:,}, {b:,}) for {','.join(kinds)}")
        else:
            jobs = args.jobs
            level = max(cov.values())
            behind = [k for k in KINDS if cov[k] < level]
            if behind:
                # A catch-up round: only the lagging kinds, and never past the
                # point the others already reached.
                kinds, a, ceiling = tuple(behind), min(cov[k] for k in behind), level
            else:
                kinds, a, ceiling = KINDS, max(lo, level), hi_final
            if ceiling is not None and a >= ceiling:
                print(f"\n  complete. results in {args.out}/")
                return 0
            # Size the round for roughly --round-seconds of wall time.
            b = a + max(int(jobs * scan_rate(a) * args.round_seconds), 10**6)
            if bounded and not behind:
                b = hi_final
            if ceiling is not None:
                b = min(b, ceiling)
            clear_shards(args.out)
            write_round(state, a, b, jobs, kinds)
            print(f"\n  round [{a:,}, {b:,})"
                  + ("" if set(kinds) == set(KINDS)
                     else f"  catch-up: {','.join(kinds)} only"))

        # A catch-up starts from zero for the kind it is rebuilding, so it
        # takes no thresholds from the run it is catching up with.
        round_seed = seed if set(kinds) == set(KINDS) else {}
        finished, front, ranges = run_round(args.out, a, b, jobs, round_seed,
                                            args.checkpoint)
        summary = merge(args.out, None, round_seed, upto=front, kinds=kinds)
        for kind in kinds:
            cov[kind] = max(cov[kind], front)
        write_coverage(args.out, cov)
        # frontier.txt is the point below which EVERY tracked sequence is
        # complete, so it is the minimum, not the maximum. While a kind is
        # catching up that reads low -- deliberately. Understating the bound
        # costs nothing; overstating it puts a false completeness claim in an
        # OEIS submission, which is the one thing this scan must never do.
        # coverage.txt carries the per-kind detail, and the resume point.
        open(frontier_file, "w").write(f"{min(cov.values())}\n")
        print(f"  merged up to {front:,}")
        for kind, (n, k, best) in summary.items():
            print(f"    {kind:<12} {n:>5} candidates -> {k:>3} records   best {best}")

        if not finished:
            print("\n  interrupted; workers checkpointed. Re-run the same "
                  "command to continue.")
            return 0
        lo = max(lo, min(cov.values()))


def _run():
    lock = None
    try:
        return main()
    finally:
        # main() sets the lock path on the module for cleanup.
        lock = globals().get("_LOCK_PATH")
        if lock and os.path.exists(lock):
            try:
                if int(open(lock).read().split()[0]) == os.getpid():
                    os.remove(lock)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(_run())
