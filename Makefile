# Modulo-210 wheel sieve

CC     ?= cc

# Highest optimisation. -march=native tunes for this machine, so the binary is
# not portable to a different CPU; override CFLAGS for a distributable build.
# -ffast-math is deliberately absent: the only floating point in the program is
# a single sqrt() at startup, so it buys nothing and relaxes FP semantics for
# free. (An -ffast-math build is what made the old floor(sqrt) bug reachable.)
CFLAGS ?= -O3 -march=native -flto -funroll-loops -std=c11 -Wall -Wextra
LDLIBS := -lm

BIN := sieve

.PHONY: all test test-slow bench clean

all: $(BIN)

$(BIN): sieve.c Makefile
	$(CC) $(CFLAGS) $< $(LDLIBS) -o $@

test: $(BIN)
	python3 test_sieve.py

# The full suite, including the million/ten-million range checks.
test-slow: $(BIN)
	python3 test_sieve.py --slow

bench: $(BIN)
	python3 bench.py

clean:
	rm -f $(BIN)
