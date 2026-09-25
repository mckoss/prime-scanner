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

.PHONY: all test test-slow test-widths test-submit bench reference clean audit submit

all: $(BIN)

$(BIN): sieve.c Makefile
	$(CC) $(CFLAGS) $< $(LDLIBS) -o $@

# Mike's 2021 drag-race entry, kept as a benchmark baseline. Built without
# -Wall -Wextra: it is a frozen reference, not code we maintain.
reference: $(REF)

$(REF): reference/mod30.c reference/prime-check.h Makefile
	$(CC) $(OPT) -std=c11 -Ireference $< -o $@

test: $(BIN) test-submit
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
# is kept beside the run it audits, in fresh/audit.txt.
audit:
	set -o pipefail; python3 -u oeis_audit.py --results fresh | tee fresh/audit.txt

# Serve oeis/submit/ so the bookmarklet can load the panel and payload. Open
# http://localhost:8017/ for the numbered worklist.
submit: audit
	@echo "  open http://localhost:8017/"
	python3 -m http.server 8017 -d oeis/submit

clean:
	rm -f $(BIN) $(REF) sieve-w8 sieve-w16 sieve-w32 sieve-w64
