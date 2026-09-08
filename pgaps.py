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
KINDS = ("gap", "lonely", "aloof")

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


def seed_from(directory):
    """Highest published/known record per kind, to seed every worker."""
    seed = {}
    for kind in KINDS:
        rows = read_records(os.path.join(directory, f"{kind}.txt")) if directory else []
        seed[kind] = max(rows, key=lambda r: r[2]) if rows else None
    return seed


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
        for _, p, _ in procs:
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
        for _, p, _ in procs:
            p.wait()
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


def merge(out, lo, seed, upto=None):
    """Apply the running-maximum rule across every worker's candidates.

    Incremental: records already in <out> are kept and act as the threshold,
    so rounds can be merged one after another.
    """
    os.makedirs(out, exist_ok=True)
    summary = {}
    for kind in KINDS:
        cands = read_records(os.path.join(out, f"{kind}.txt"))
        for d in sorted(os.listdir(os.path.join(out, "shards"))):
            cands += read_records(os.path.join(out, "shards", d, f"{kind}.txt"))
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
        finished = monitor(out, procs, ranges)
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
    args = ap.parse_args()

    if not os.path.exists(BINARY):
        sys.exit("./sieve not built -- run 'make' first")

    os.makedirs(args.out, exist_ok=True)
    seed = seed_from(args.seed)
    state = os.path.join(args.out, "round.txt")

    if args.merge_only:
        if not os.path.exists(state):
            sys.exit(f"{state} missing -- nothing to merge")
        lo, hi, jobs = (int(x) for x in open(state).read().split())
        ranges = prepare(args.out, jobs, lo, hi, seed)
        front = safe_frontier(args.out, ranges)
        summary = merge(args.out, None, seed, upto=front)
        for kind, (n, k, best) in summary.items():
            print(f"    {kind:<7} {n:>5} candidates -> {k:>3} records   best {best}")
        return 0

    # An unfinished round takes precedence: resume it before advancing.
    resume = None
    if os.path.exists(state):
        a, b, j = (int(x) for x in open(state).read().split())
        ranges = prepare(args.out, j, a, b, seed)
        if any(not is_done(args.out, i) for i in range(j)):
            resume = (a, b, j)

    lo = int(args.lo)
    frontier_file = os.path.join(args.out, "frontier.txt")
    if os.path.exists(frontier_file):
        lo = max(lo, int(open(frontier_file).read().strip()))

    bounded = args.hi is not None
    hi_final = int(args.hi) if bounded else None
    if bounded and lo >= hi_final:
        print("  nothing to do: frontier is already at or past --to")
        return 0

    if resume:
        where = f"resuming round [{resume[0]:,}, {resume[1]:,})"
    elif bounded:
        where = f"scanning [{lo:,}, {hi_final:,})"
    else:
        where = f"scanning from {lo:,}, open-ended"
    print(f"  {where} across {args.jobs} workers")
    for kind in KINDS:
        row = seed.get(kind)
        print(f"    {kind:<7} seed threshold {row[2] if row else 0}")

    while True:
        if resume:
            a, b, jobs = resume
            resume = None
            print(f"\n  resuming round [{a:,}, {b:,})")
        else:
            jobs = args.jobs
            a = lo
            if bounded:
                b = hi_final
            else:
                # Size the round for roughly --round-seconds of wall time.
                b = a + max(int(jobs * scan_rate(a) * args.round_seconds), 10**6)
            clear_shards(args.out)
            open(state, "w").write(f"{a} {b} {jobs}\n")
            print(f"\n  round [{a:,}, {b:,})")

        finished, front, ranges = run_round(args.out, a, b, jobs, seed,
                                            args.checkpoint)
        summary = merge(args.out, None, seed, upto=front)
        open(frontier_file, "w").write(f"{front}\n")
        print(f"  merged up to {front:,}")
        for kind, (n, k, best) in summary.items():
            print(f"    {kind:<7} {n:>5} candidates -> {k:>3} records   best {best}")

        if not finished:
            print("\n  interrupted; workers checkpointed. Re-run the same "
                  "command to continue.")
            return 0
        lo = b
        if bounded and lo >= hi_final:
            print(f"\n  complete. results in {args.out}/")
            return 0


if __name__ == "__main__":
    sys.exit(main())
