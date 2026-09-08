# Modulo-210 wheel sieve

CC  ?= cc

# Highest optimisation. -march=native tunes for this machine, so the binary is
# not portable to a different CPU; override OPT for a distributable build.
# -ffast-math is deliberately absent: the only floating point in the program is
# a single sqrt() at startup, so it buys nothing and relaxes FP semantics for
# free. (An -ffast-math build is what made the old floor(sqrt) bug reachable.)
OPT    ?= -O3 -march=native -flto -funroll-loops
CFLAGS ?= $(OPT) -std=c11 -Wall -Wextra
LDLIBS := -lm

BIN := sieve
REF := reference/mod30

.PHONY: all test test-slow bench reference clean

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

bench: $(BIN) $(REF)
	python3 bench.py

clean:
	rm -f $(BIN) $(REF)
