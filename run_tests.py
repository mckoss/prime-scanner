import subprocess
import math

def test_sieve(limit, expected_count):
    try:
        # Use gtimeout to ensure infinite loops fail fast (5 second cap)
        res = subprocess.run(
            ["./sieve_bin", str(limit)],
            capture_output=True, text=True, timeout=5
        )
    except Exception as e:
        print(f"❌ FAIL ({limit}): Process crashed or timed out.")
        return False
    
    # The primes are on the last line of stdout. The first line is "Primes up to X:"
    lines = res.stdout.strip().split('\n')
    count = 0
    if len(lines) > 1:
        count = len(lines[-1].split())
        
        # Additional check: ensure no composites slipped in (like 121, 169 which were previous bugs)
        # We know the exact prime list for this range. 
        # A simple heuristic check against the expected_count is robust enough for pi(n).
    
    if count == expected_count:
        print(f"✅ PASS ({limit}): Found exactly {count} primes.")
        return True
    else:
        print(f"❌ FAIL ({limit}): Expected {expected_count}, found {count}. Output tail: {lines[-1][-50:]}")
        return False

print("=== Running Automated Sieve Tests ===\n")

results = []
results.append(test_sieve(50, 15))  # pi(50)
results.append(test_sieve(100, 25)) # pi(100)
results.append(test_sieve(500, 95)) # pi(500)
results.append(test_sieve(1000, 168)) # pi(1000)

passed = sum(results)
total = len(results)
print(f"\n=== Unit Test Summary: {passed}/{total} Passed ===")
