#!/bin/bash
set -e

echo "Running QueryBridge Tests"
echo "========================="

# Function to run a test case
run_test() {
  local test_name=$1
  local schema_path="test/$test_name/schema.graphql"
  local query_path="test/$test_name/query.graphql"
  local result_path="test/$test_name/result.xsb"
  local output_path="test/$test_name/output.xsb"
  
  echo -e "\n\033[1;36mRunning Test: $test_name\033[0m"
  echo "Schema: $schema_path"
  echo "Query: $query_path"
  
  # Create directory if it doesn't exist
  mkdir -p "$(dirname "$output_path")"
  
  # Run the QueryBridge command
  ./build/bin/querybridge "$schema_path" "$query_path" "$output_path"
  
  # Compare with expected result
  echo -e "\nComparing with expected result..."
  echo "Expected result:"
  cat "$result_path"
  echo -e "\nActual result:"
  cat "$output_path"
  
  # Perform diff
  if diff -w "$result_path" "$output_path" > /dev/null; then
    echo -e "\033[1;32mTest PASSED ✓\033[0m"
    return 0
  else
    echo -e "\033[1;31mTest FAILED ✗\033[0m"
    echo "Differences:"
    diff -w "$result_path" "$output_path"
    return 1
  fi
}

# Run the basic test case
echo -e "\n\033[1;33m== Running Basic Test Case ==\033[0m"
run_test "basic"

# Run the nested tables test case
echo -e "\n\033[1;33m== Running Nested Tables Test Case ==\033[0m"
run_test "nested_tables"

# Run the bad normalization test case
echo -e "\n\033[1;33m== Running Bad Normalization Test Case ==\033[0m"
run_test "bad_normalization"

# Run the window functions test case
echo -e "\n\033[1;33m== Running Window Functions Test Case ==\033[0m"
run_test "window_functions"

echo -e "\n\033[1;33m== Test Summary ==\033[0m"
echo "All tests completed"