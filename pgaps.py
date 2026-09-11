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
import contextlib
import os
import select
import signal
import subprocess
import sys
import termios
import time
import tty

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


def read_frontiers(out):
    """Each kind's own frontier: how far it has been scanned, from zero.

    They are equal in a settled run. Adding a kind to KINDS puts it at 0 while
    the rest stay where they are, which is why the frontier has to be recorded
    per sequence rather than as one number for the run.

    BACKWARD COMPATIBILITY. Two older shapes exist and mean different things:

    * A single-number frontier.txt, written by this driver before the format
      changed. It means "scanned contiguously to F, and the merged files are
      truncated to F". That scan collected exactly the kinds the sieve of the
      day knew about, and merged them all with the same bound -- so every kind
      that HAS a records file is at F, and a kind with no records file was
      never collected at all and is at 0. That second case is precisely the
      state a newly added kind is in, which is what makes the inference exact
      rather than a guess.

    * No frontier.txt, e.g. results/, the original single-threaded scan. Its
      position lives in progress.txt, and that is deliberately NOT read here.
      A serial position means "the last prime visited", which coincides with a
      frontier only for a run that started at zero; this driver's frontier
      means "provably contiguous across all shards". Treating one as the other
      would let a seeded run masquerade as an exhaustive one, so such a
      directory reads as 0 -- rescan from scratch, which is always safe.
    """
    fronts = {k: 0 for k in KINDS}
    path = os.path.join(out, "frontier.txt")
    if not os.path.exists(path):
        return fronts

    text = open(path).read()
    head = text.split()
    if head and head[0].isdigit():                  # legacy: one number
        legacy = int(head[0])
        for k in KINDS:
            if os.path.exists(os.path.join(out, f"{k}.txt")):
                fronts[k] = legacy
        return fronts

    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        f = line.split()
        if len(f) >= 2 and f[0] in fronts:
            fronts[f[0]] = int(f[1])
    return fronts


def write_frontiers(out, fronts):
    with open(os.path.join(out, "frontier.txt"), "w") as f:
        f.write("# Each sequence's frontier: scanned contiguously from zero to\n"
                "# here. Equal in a settled run; a sequence added later sits\n"
                "# behind until the scan catches it up.\n")
        for k in KINDS:
            f.write(f"{k} {fronts.get(k, 0)}\n")


def est_seconds(lo, hi, jobs):
    """Rough wall time to scan [lo, hi) on `jobs` workers.

    RATE_POINTS are per-worker; 0.549 is the measured per-worker efficiency at
    8 workers. Only used to tell the user how long a catch-up will take.
    """
    if hi <= lo:
        return 0.0
    n, tot, x = 500, 0.0, max(lo, 1e6)
    for i in range(1, n + 1):
        y = max(lo, 1e6) * (hi / max(lo, 1e6)) ** (i / n)
        tot += (y - x) / scan_rate((x + y) / 2)
        x = y
    return tot / max(jobs * 0.549, 1e-9)


def plan_round(fronts, args, jobs):
    """(kinds, lo, ceiling) for the next round.

    The scan resumes at the LOWEST frontier and collects every sequence that
    has reached it. It stops at the next frontier above -- so when the scan
    arrives there, that sequence rolls in and is collected from then on,
    instead of being under-collected across part of a round.
    """
    a = min(fronts.values())
    if len(set(fronts.values())) == 1:
        a = max(a, int(args.lo))
    kinds = tuple(k for k in KINDS if fronts[k] <= a)
    above = sorted(v for v in set(fronts.values()) if v > a)
    ceiling = above[0] if above else None
    if args.hi is not None:
        hi = int(args.hi)
        ceiling = hi if ceiling is None else min(ceiling, hi)
    return kinds, a, ceiling


def confirm(prompt):
    if not sys.stdin.isatty():
        return False
    try:
        return input(prompt).strip().lower() in ("y", "yes")
    except EOFError:
        return False


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
    # Column spec only, like every other data file. What this one IS belongs
    # in fresh/README.md, not repeated at the top of the data.
    write_records(os.path.join(out, "balanced.txt"), rows,
                  "# balanced-lonely records: <n> <prime> <value> <gap_below> "
                  "<gap_above> <prev_prime> <next_prime>\n")
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


@contextlib.contextmanager
def cbreak_stdin():
    """Deliver single keypresses without waiting for Enter.

    Yields None when stdin is not a terminal -- under nohup, a pipe or a
    cron job there is nothing to put into cbreak, and the scan still has to
    run. The old terminal settings are restored on every exit path, including
    Ctrl-C, or the shell is left with echo off.
    """
    if not sys.stdin.isatty():
        yield None
        return
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield fd
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def wait_key(fd, timeout):
    """The next keypress, or None if `timeout` seconds pass without one."""
    if fd is None:
        time.sleep(timeout)
        return None
    end = time.time() + timeout
    while True:
        left = end - time.time()
        if left <= 0:
            return None
        if select.select([fd], [], [], left)[0]:
            return os.read(fd, 1).decode("utf-8", "replace")


def monitor(out, procs, ranges, interval=15):
    """Report progress until the workers finish; space pauses and resumes.

    SIGSTOP is safe for these workers: they time themselves with clock(), so
    a stopped worker's checkpoint clock does not advance and nothing is
    re-scanned on resume. Paused time is kept out of the rate below for the
    same reason -- it is not time the scan spent working.
    """
    started = time.time()
    paused, paused_since, paused_total = False, 0.0, 0.0

    def signal_all(sig):
        for _, p, _ in procs:
            if p.poll() is None:
                try:
                    p.send_signal(sig)
                except ProcessLookupError:
                    pass

    try:
        with cbreak_stdin() as fd:
            while any(p.poll() is None for _, p, _ in procs):
                if wait_key(fd, interval) == " ":
                    paused = not paused
                    if paused:
                        signal_all(signal.SIGSTOP)
                        paused_since = time.time()
                        print("  paused -- space to resume", flush=True)
                    else:
                        signal_all(signal.SIGCONT)
                        paused_total += time.time() - paused_since
                        print("  resumed", flush=True)
                    continue
                if paused:
                    continue

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
                el = time.time() - started - paused_total
                print(f"  [{el:7.0f}s] {done}/{len(procs)} workers done  "
                      f"{100.0 * scanned / total:5.1f}% of range  "
                      f"{scanned / max(el, 1e-9):.2e} nums/s aggregate", flush=True)
    except KeyboardInterrupt:
        print("\n  interrupted -- signalling workers to checkpoint", flush=True)
        # A stopped worker cannot act on SIGTERM, so it would never reach its
        # checkpoint and kill_workers() would fall through to SIGKILL.
        if paused:
            signal_all(signal.SIGCONT)
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

        # Header describes the DATA, and nothing about the run that produced
        # it. A candidate count changes every round while the records do not,
        # so recording it here churns a committed data file for no reason --
        # it was once the only line differing between two snapshots. The live
        # counts go to stdout in the round summary instead.
        write_records(os.path.join(out, f"{kind}.txt"), kept,
                      f"# {kind} records: <n> <prime> <value> <gap_below> "
                      f"<gap_above> <prev_prime> <next_prime>\n")
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
                    help="print each sequence's frontier, and exit")
    ap.add_argument("--catch-up", dest="catch_up", action="store_true",
                    help="proceed without asking when the sequences' frontiers "
                         "diverge and one has to be caught up")
    args = ap.parse_args()

    if not os.path.exists(BINARY):
        sys.exit("./sieve not built -- run 'make' first")

    os.makedirs(args.out, exist_ok=True)
    install_signal_handlers()
    globals()["_LOCK_PATH"] = acquire_lock(args.out)
    seed = seed_from(args.seed)
    state = os.path.join(args.out, "round.txt")

    fronts = read_frontiers(args.out)
    settled = len(set(fronts.values())) == 1

    if args.status:
        print(f"  {args.out}/")
        level = max(fronts.values())
        for kind in KINDS:
            n = len(read_records(os.path.join(args.out, f"{kind}.txt")))
            flag = "" if fronts[kind] >= level else \
                   f"   <-- {level - fronts[kind]:,} behind"
            print(f"    {kind:<12} {n:>3} records   frontier "
                  f"{fronts[kind]:,}{flag}")
        if not settled:
            print("  frontiers diverge; a run will catch the lagging ones up")
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

    # Diverged frontiers are worth stopping for: the run is about to spend
    # real time re-scanning ground it has already covered, and the plan is
    # not what someone typing the usual command expects.
    if not settled:
        level = max(fronts.values())
        low = min(fronts.values())
        behind = [k for k in KINDS if fronts[k] < level]
        print(f"\n  !! frontiers diverge in {args.out}/")
        for kind in KINDS:
            mark = "  <-- behind" if fronts[kind] < level else ""
            print(f"       {kind:<12} {fronts[kind]:>22,}{mark}")
        hrs = est_seconds(low, level, args.jobs) / 3600.0
        print(f"\n     plan: scan up from {low:,}, collecting "
              f"{', '.join(behind)} only,")
        rolled = [k for k in KINDS if k not in behind]
        print(f"           rolling in {', '.join(rolled)} on reaching "
              f"{level:,}.")
        print(f"           roughly {hrs:.1f}h to level at {args.jobs} workers. "
              f"The others' files")
        print(f"           are not written until then.")
        if resume:
            print(f"\n     first, the unfinished round [{resume[0]:,}, "
                  f"{resume[1]:,}) is resumed.")
        if not args.catch_up and not confirm("\n  proceed? [y/N] "):
            print("  stopped. Re-run with --catch-up to skip this question.")
            return 0

    if resume:
        where = f"resuming round [{resume[0]:,}, {resume[1]:,})"
    else:
        _, a0, ceil0 = plan_round(fronts, args, args.jobs)
        where = (f"scanning [{a0:,}, {int(args.hi):,})" if args.hi is not None
                 else f"scanning from {a0:,}, open-ended")
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
            # merged as though they covered the range from zero. A kind whose
            # frontier reaches the round's start was being collected by it.
            kinds = tuple(k for k in kinds if fronts[k] >= a)
            if not kinds:
                print(f"\n  discarding round [{a:,}, {b:,}): it collected "
                      f"nothing still wanted")
                clear_shards(args.out)
                continue
            print(f"\n  resuming round [{a:,}, {b:,}) for {','.join(kinds)}")
        else:
            jobs = args.jobs
            kinds, a, ceiling = plan_round(fronts, args, jobs)
            if ceiling is not None and a >= ceiling:
                print(f"\n  complete. results in {args.out}/")
                return 0
            # Size the round for roughly --round-seconds of wall time, and
            # never step past the next frontier: that is where a sequence
            # rolls in, and it has to roll in on a round boundary.
            b = a + max(int(jobs * scan_rate(a) * args.round_seconds), 10**6)
            if ceiling is not None:
                b = min(b, ceiling)
            clear_shards(args.out)
            write_round(state, a, b, jobs, kinds)
            print(f"\n  round [{a:,}, {b:,})"
                  + ("" if set(kinds) == set(KINDS)
                     else f"  catching up: {','.join(kinds)} only"))

        # A sequence being caught up is rebuilt from zero, so it takes no
        # threshold from the run it is catching up with.
        round_seed = seed if set(kinds) == set(KINDS) else {}
        finished, front, ranges = run_round(args.out, a, b, jobs, round_seed,
                                            args.checkpoint)
        summary = merge(args.out, None, round_seed, upto=front, kinds=kinds)
        for kind in kinds:
            fronts[kind] = max(fronts[kind], front)
        write_frontiers(args.out, fronts)
        print(f"  merged up to {front:,}")
        for kind, (n, k, best) in summary.items():
            print(f"    {kind:<12} {n:>5} candidates -> {k:>3} records   best {best}")

        if not finished:
            print("\n  interrupted; workers checkpointed. Re-run the same "
                  "command to continue.")
            return 0
        if len(set(fronts.values())) == 1 and not settled:
            settled = True
            print(f"\n  all sequences level at {min(fronts.values()):,}; "
                  f"scanning them together from here")


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
