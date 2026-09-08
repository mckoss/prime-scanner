# Modulo-210 wheel sieve

CC  ?= cc

# Highest optimisation. -march=native tunes for this machine, so the binary is
# not portable to a different CPU; override OPT for a distributable build.
# -ffast-math is deliberately absent: the only floating point in the program is
# a single sqrt() at startup, so it buys nothing and relaxes FP semantics for
# free. (An -ffast-math build is what made the old floor(sqrt) bug reachable.)
OPT    ?= -O3 -march=native -flto -funroll-loops

# Sieve bitmap word size: 8, 16, 32 or 64. No width wins at every limit --
# see the table in sieve.c. 32 is never the worst; 64 is best above ~3e6.
WORD_BITS ?= 32

CFLAGS ?= $(OPT) -std=c11 -Wall -Wextra -DSIEVE_WORD_BITS=$(WORD_BITS)
LDLIBS := -lm

BIN := sieve
REF := reference/mod30

.PHONY: all test test-slow test-widths bench reference clean

all: $(BIN)

$(BIN): sieve.c Makefile
	$(CC) $(CFLAGS) $< $(LDLIBS) -o $@

# Mike's 2021 drag-race entry, kept as a benchmark baseline. Built without
# -Wall -Wextra: it is a frozen reference, not code we maintain.
reference: $(REF)

$(REF): reference/mod30.c reference/prime-check.h Makefile
	$(CC) $(OPT) -std=c11 -Ireference $< -o $@

test: $(BIN)
	python3 test_sieve.py

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

clean:
	rm -f $(BIN) $(REF) sieve-w8 sieve-w16 sieve-w32 sieve-w64
