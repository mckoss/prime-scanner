# Modulo-210 wheel sieve

CC  ?= cc

# Highest optimisation. -march=native tunes for this machine, so the binary is
# not portable to a different CPU; override OPT for a distributable build.
# -ffast-math is deliberately absent: the only floating point in the program is
# a single sqrt() at startup, so it buys nothing and relaxes FP semantics for
# free. (An -ffast-math build is what made the old floor(sqrt) bug reachable.)
OPT    ?= -O3 -march=native -flto -funroll-loops

# Sieve bitmap word size: 8, 16, 32 or 64. See the table in sieve.c: 64 wins
# from 1e6 up, and trails 32 by under 10% below that.
WORD_BITS ?= 64

CFLAGS ?= $(OPT) -std=c11 -Wall -Wextra -DSIEVE_WORD_BITS=$(WORD_BITS)
LDLIBS := -lm

BIN := sieve
REF := reference/mod30

.PHONY: all test test-slow test-widths test-submit bench reference clean audit audit-refresh oeis-refresh oeis-readme submit pgaps graph

all: $(BIN)

# Resume the fresh scan with one worker per CPU core. Override PGAPS_OUT,
# PGAPS_WORKERS (e.g. '--jobs 8'), or PGAPS_ARGS (e.g. '--to 1e14') as needed.
PGAPS_OUT ?= fresh
PGAPS_WORKERS ?= --all-cores
PGAPS_ARGS ?=

pgaps: $(BIN)
	python3 -u pgaps.py --out $(PGAPS_OUT) $(PGAPS_WORKERS) $(PGAPS_ARGS)

# Rebuild the README graph from fresh b-files and published gap primes.
graph: docs/prime-sequences.svg

docs/prime-sequences.svg: plot_sequences.py fresh/gap.txt fresh/lonely.txt fresh/aloof.txt fresh/equidistant.txt fresh/balanced.txt fresh/pairwise.txt oeis/gap.txt
	python3 plot_sequences.py

$(BIN): sieve.c Makefile
	$(CC) $(CFLAGS) $< $(LDLIBS) -o $@

# Mike's 2021 drag-race entry, kept as a benchmark baseline. Built without
# -Wall -Wextra: it is a frozen reference, not code we maintain.
reference: $(REF)

$(REF): reference/mod30.c reference/prime-check.h Makefile
	$(CC) $(OPT) -std=c11 -Ireference $< -o $@

test: $(BIN) test-submit
	python3 test_audit.py
	python3 test_oeis_readme.py
	python3 test_sieve.py

# Checks oeis/submit/ before any of it goes to OEIS: b-file spec compliance,
# ASCII, attribution headers, agreement with the published b-files, and the
# shapes the browser tooling relies on. The fill.js half needs node; without
# it the Python half still runs.
test-submit:
	python3 test_submit.py
	@command -v node >/dev/null && node test_fill.js \
		|| echo "  (skipped test_fill.js: no node)"

# The full suite, including the million/ten-million range checks.
test-slow: $(BIN)
	python3 test_sieve.py --slow

# The packing arithmetic differs per word size, so verify each one.
test-widths:
	@for w in 8 16 32 64; do \
		echo "--- WORD_BITS=$$w ---"; \
		$(CC) $(OPT) -std=c11 -Wall -Wextra -DSIEVE_WORD_BITS=$$w sieve.c $(LDLIBS) \
			-o sieve-w$$w || exit 1; \
		python3 test_sieve.py --binary ./sieve-w$$w || exit 1; \
	done; rm -f sieve-w8 sieve-w16 sieve-w32 sieve-w64

bench: $(BIN) $(REF)
	python3 bench.py

# Regenerate oeis/submit/ -- the edit script, the b-files and a-files to
# upload, and the browser tooling that fills the OEIS edit form. The report
# is kept beside the run it audits, in fresh/audit.md.
audit:
	python3 -u oeis_audit.py --results fresh --markdown fresh/audit.md
	python3 oeis_readme.py

# Refetch the committed b-file snapshots in oeis/*.txt from OEIS. Review and
# commit the diff: a newly published term is one a scan can no longer claim.
oeis-refresh:
	python3 check_oeis.py --refresh

# The audit, after refetching everything it reads from OEIS: the snapshots
# above, then entries, other b-files, a-files and citing searches.
audit-refresh: oeis-refresh
	python3 -u oeis_audit.py --refresh --results fresh --markdown fresh/audit.md
	python3 oeis_readme.py

# Refresh just the scan-dependent parts of oeis/README.md from local files.
# This verifies the records against the committed OEIS snapshots first.
oeis-readme:
	python3 oeis_readme.py

# Serve oeis/submit/ so the bookmarklet can load the panel and payload. Open
# http://localhost:8017/ for the numbered worklist.
submit: audit
	@echo "  open http://localhost:8017/"
	python3 -m http.server 8017 -d oeis/submit

clean:
	rm -f $(BIN) $(REF) sieve-w8 sieve-w16 sieve-w32 sieve-w64
