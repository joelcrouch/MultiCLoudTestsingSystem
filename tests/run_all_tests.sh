#!/bin/bash

# Record start time
start_time=$(date +%s)

GREEN_EXIT_CODE=0
PYTEST_EXIT_CODE=0

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print a colored message in a "box"
print_box_message() {
    COLOR=$1
    MESSAGE=$2
    LINE_LENGTH=${#MESSAGE}
    BORDER_LINE=$(printf '─%.0s' $(seq 1 $((LINE_LENGTH + 4)))) # +4 for padding

    echo -e "${COLOR}┌${BORDER_LINE}┐${NC}"
    echo -e "${COLOR}│  ${MESSAGE}  │${NC}"
    echo -e "${COLOR}└${BORDER_LINE}┘${NC}"
}

echo "--- Running unittest-style tests with green ---"
time green tests/auth tests/communication tests/config tests/coordination
GREEN_EXIT_CODE=$?

if [ "$GREEN_EXIT_CODE" -ne 0 ]; then
    echo "Green tests failed!"
fi

echo ""
echo "--- Running pytest-style tests with pytest ---"
time PYTHONPATH=. pytest --cov=src --cov-report=html tests/pipeline/test_ingestion_engine.py tests/pipeline/test_processing_workers.py tests/pipeline/test_distribution_coordinator.py tests/pipeline/test_storage_manager.py tests/integration/test_full_pipeline.py tests/integration/test_cross_cloud_flow.py tests/integration/test_large_scale_pipeline.py tests/monitoring/test_monitoring.py
PYTEST_EXIT_CODE=$?

if [ "$PYTEST_EXIT_CODE" -ne 0 ]; then
    echo "Pytest tests failed!"
fi

echo ""
echo "--- Overall Test Summary ---"

# Record end time and calculate duration
end_time=$(date +%s)
duration=$((end_time - start_time))
echo "Total execution time: ${duration} seconds"
echo ""


if [ "$GREEN_EXIT_CODE" -eq 0 ] && [ "$PYTEST_EXIT_CODE" -eq 0 ]; then
    print_box_message "$GREEN" "✅ All test suites passed successfully!"
    exit 0
else
    print_box_message "$RED" "❌ Some test suites failed. Please review the output above for details."
    exit 1
fi