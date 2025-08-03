#!/usr/bin/env python3
"""
Test suite runner for the Knowledge Base system.
Runs all unit and integration tests and provides a summary.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def run_test_file(test_file):
    """Run a single test file and return results."""
    print(f"\n{'='*60}")
    print(f"Running {test_file}...")
    print('='*60)
    
    start_time = time.time()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    duration = time.time() - start_time
    
    return {
        'file': test_file,
        'passed': result.returncode == 0,
        'duration': duration,
        'stdout': result.stdout,
        'stderr': result.stderr
    }


def extract_test_stats(output):
    """Extract test statistics from pytest output."""
    lines = output.split('\n')
    for line in lines:
        if 'passed' in line and ('failed' in line or 'error' in line or line.endswith('passed')):
            return line.strip()
    return "No test statistics found"


def main():
    """Run all tests and provide summary."""
    print("🧪 Knowledge Base Test Suite Runner")
    print("="*60)
    
    # Find all test files in the current tests directory
    tests_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    test_files = sorted(tests_dir.glob('test_*.py'))
    
    if not test_files:
        print("❌ No test files found!")
        return 1
    
    print(f"Found {len(test_files)} test files:")
    for tf in test_files:
        print(f"  - {tf}")
    
    # Run each test file
    results = []
    for test_file in test_files:
        result = run_test_file(str(test_file))
        results.append(result)
        
        # Print immediate result
        if result['passed']:
            stats = extract_test_stats(result['stdout'])
            print(f"✅ PASSED: {stats}")
        else:
            print(f"❌ FAILED")
            if result['stderr']:
                print("STDERR:", result['stderr'][:200])
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print('='*60)
    
    total_duration = sum(r['duration'] for r in results)
    passed_count = sum(1 for r in results if r['passed'])
    failed_count = len(results) - passed_count
    
    print(f"\nTotal test files: {len(results)}")
    print(f"✅ Passed: {passed_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⏱️  Total duration: {total_duration:.2f}s")
    
    # Detailed results
    print("\nDetailed Results:")
    for result in results:
        status = "✅ PASSED" if result['passed'] else "❌ FAILED"
        print(f"  {result['file']:30} {status} ({result['duration']:.2f}s)")
    
    # Run combined test report
    print(f"\n{'='*60}")
    print("Running combined test report...")
    print('='*60)
    
    # Run pytest from the parent directory to get proper coverage
    parent_dir = os.path.dirname(tests_dir)
    combined_result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "--cov=.", "--cov-report=term-missing"],
        capture_output=True,
        text=True,
        cwd=parent_dir
    )
    
    if "pytest-cov" in combined_result.stderr:
        print("Note: Install pytest-cov for coverage reports: pip install pytest-cov")
    else:
        # Extract and print key statistics
        lines = combined_result.stdout.split('\n')
        in_coverage = False
        for line in lines:
            if 'TOTAL' in line or '=====' in line or 'passed' in line:
                print(line)
            elif line.startswith('Name'):
                in_coverage = True
            if in_coverage and line.strip():
                print(line)
    
    # Final status
    print(f"\n{'='*60}")
    if failed_count == 0:
        print("🎉 All tests passed! The Knowledge Base system is ready.")
        return 0
    else:
        print(f"⚠️  {failed_count} test file(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())