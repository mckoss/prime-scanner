#!/bin/bash

echo "=== 1. Compiling sieve.c ==="
gcc -O3 -ffast-math -march=native sieve.c -lm -o ./sieve_bin 2>&1
if [ $? -ne 0 ]; then echo "❌ Compilation failed!"; exit 1; fi
echo "✅ Binary compiled successfully.\n"

PASS=0
FAIL=0

run_test() {
    local name="$1"
    local lim="$2"
    local expected="$3"
    
    echo -n "Test: $name ($lim)... "
    
    # Run with gtimeout to prevent infinite hangs (limit to 5 seconds)
    local output=$(gtimeout 5 ./sieve_bin "$lim" 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo "❌ FAIL (Timeout or Crash!)"
        ((FAIL++))
        return
    fi

    # Count primes: they appear after the header line "Primes up to X:"
    local count=$(echo "$output" | tail -n +2 | wc -w)
    
    if [ "$count" -eq "$expected" ]; then
        echo "✅ PASS (Found $count)"
        ((PASS++))
    else
        echo "❌ FAIL (Found $count instead of $expected)"
        ((FAIL++))
    fi
}

echo "=== 2. Running Unit Tests ===\n"

run_test "Small Limit" 50 15
run_test "Standard Limit" 100 25
run_test "Mid Limit" 500 95
run_test "Large Limit (Speed)" 10000 1229

# Check specific missing primes in the wheel gaps
echo -n "Test: Checking specific wheel gap primes... "
local out=$(gtimeout 5 ./sieve_bin 200 >/dev/null 2>&1)
if grep -qw "197" <<< "./sieve_bin 200" && grep -qw "199" <<< "./sieve_bin 200"; then
    echo "✅ PASS"
    ((PASS++))
else
    echo "❌ FAIL"
    ((FAIL++))
fi

echo "\n=== Summary ==="
echo "Total: $((PASS + FAIL)) | Passed: $PASS | Failed: $FAIL"
exit 0
