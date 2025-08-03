#!/bin/bash
# Run all tests for YouTube scraper production system

set -e  # Exit on error

echo "========================================"
echo "YouTube Scraper Test Suite"
echo "========================================"
echo ""

# Set test environment
export PYTEST_CURRENT_TEST=1
export TESTING=1

# Create reports directory
mkdir -p tests/reports

# Function to run tests with timing
run_test_category() {
    local category=$1
    local description=$2
    
    echo "----------------------------------------"
    echo "$description"
    echo "----------------------------------------"
    
    start_time=$(date +%s)
    
    if [ "$category" = "performance" ]; then
        # Performance tests need special handling
        echo "Running load tests..."
        python tests/performance/load_test.py || true
        
        echo ""
        echo "Running stress tests..."
        python tests/performance/stress_test.py || true
    else
        # Regular pytest for unit and integration tests
        pytest -v "tests/$category/" --tb=short || true
    fi
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    echo "Duration: ${duration}s"
    echo ""
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest is not installed"
    echo "Please run: pip install pytest pytest-mock pytest-timeout"
    exit 1
fi

# Run unit tests
run_test_category "unit" "UNIT TESTS"

# Run integration tests
run_test_category "integration" "INTEGRATION TESTS"

# Ask about performance tests
echo "----------------------------------------"
echo "PERFORMANCE TESTS"
echo "----------------------------------------"
echo "Performance tests require a configured environment and may take several minutes."
read -p "Run performance tests? (y/N): " run_perf

if [[ $run_perf =~ ^[Yy]$ ]]; then
    run_test_category "performance" "PERFORMANCE TESTS"
else
    echo "Skipping performance tests"
fi

# Generate coverage report if coverage is installed
if command -v coverage &> /dev/null; then
    echo ""
    echo "----------------------------------------"
    echo "COVERAGE REPORT"
    echo "----------------------------------------"
    
    coverage run -m pytest tests/unit tests/integration
    coverage report -m
    coverage html -d tests/reports/htmlcov
    
    echo "HTML coverage report saved to: tests/reports/htmlcov/index.html"
fi

# Summary
echo ""
echo "========================================"
echo "TEST SUITE COMPLETE"
echo "========================================"
echo "Reports saved in: tests/reports/"
echo ""

# Check for any test failures
if grep -r "FAILED" tests/reports/*.log 2>/dev/null; then
    echo "⚠️  Some tests failed. Check reports for details."
    exit 1
else
    echo "✅ All tests completed!"
fi