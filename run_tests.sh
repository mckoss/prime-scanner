#!/bin/bash

PASS=0
FAIL=0
TOTAL=0

# 1. Test small limits where exact counts are known (Pi(50)=15, Pi(100)=25)
run_test() {
    local name="$1"
    local lim="$2"
    local expected_cnt="$3"
    
    ((TOTAL++))
    echo -n "Test ${TOTAL} ('$name' limit=$lim...): "

    # Ensure infinite loops don't hang the testing process
    local output=$(gtimeout 4 ./sieve_bin "$lim" 2>/dev/null || echo "")
    
    if [ -z "$output" ]; then
        echo "💥 CRASH/TIMEOUT!"
        ((FAIL++))
        return
    fi
    
    # Count printed integers (excluding the header line)
    local count=$(echo "$output" | tail -n +2 | wc -w)
    
    if [ "$count" -eq "$expected_cnt" ]; then
        echo "✅ PASS (Found exactly $count primes)"
        ((PASS++))
    else
        echo "❌ FAIL (Expected $expected_cnt, found $count)"
        ((FAIL++))
    fi
}

# 2. Test default behavior (limit=500, expected count is 95)
run_test "Small Limits" 50 15
run_test "Standard Limit" 100 25

echo -n "Test $((TOTAL+1)) (Default limit=500): "
output=$(gtimeout 4 ./sieve_bin | tail -n +2 | wc -w)
if [ "$output" -eq 95 ]; then echo "✅ PASS"; ((PASS++)); else echo "❌ FAIL (Found $output)"; ((FAIL++)); fi

# 3. Test large prime candidates specifically to verify wheel gap logic
echo -n "Test $((TOTAL+2)) (Wheel Candidates): "
if gtimeout 4 ./sieve_bin 200 | grep -qw "197" && gtimeout 4 ./sieve_bin 200 | grep -qw "199"; then
    echo "✅ PASS (Correctly identified residues in wheel gaps)"
    ((PASS++))
else
    echo "❌ FAIL"
    ((FAIL++))
fi

# 4. Verify --help output
echo -n "Test $((TOTAL+3)) (Help Flag): "
./sieve_bin --help > /dev/null 2>&1; status=$?
if [ $status -eq 0 ]; then echo "✅ PASS"; ((PASS++)); else echo "❌ FAIL"; ((FAIL++)); fi

echo "\n=== Summary ==="
echo "Passed: $PASS / $TOTAL Total"
exit "$FAIL"
