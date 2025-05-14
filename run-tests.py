#!/usr/bin/env python3
"""
Test runner for QueryBridge.

This script runs the test cases in the tests directory.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

try:
    # Try importing from installed package
    from querybridge.translator import translate_graphql_to_xsb
except ImportError:
    try:
        # Try importing directly from source
        sys.path.insert(0, str(project_root / "src"))
        from querybridge.translator import translate_graphql_to_xsb
    except ImportError:
        print("Error: Unable to import QueryBridge modules.")
        print("Make sure you have installed the required packages:")
        print("  pip install -e .")
        print("  pip install graphql-core")
        sys.exit(1)


def run_single_test(test_dir: Path, keep_output: bool = False) -> bool:
    """
    Run a single test from the given test directory.
    
    Args:
        test_dir: Path to the test directory
        keep_output: Whether to keep output files after test execution
        
    Returns:
        True if the test passes, False otherwise
    """
    test_name = test_dir.name
    print(f"\n{'='*40}")
    print(f"Running test: {test_name}")
    print(f"{'='*40}")
    
    schema_path = test_dir / "schema.graphql"
    query_path = test_dir / "query.graphql"
    facts_path = test_dir / "facts.xsb"  # Original facts file
    facts_p_path = test_dir / "facts.P"  # Facts file for XSB
    
    if not schema_path.exists() or not query_path.exists():
        print(f"Error: Missing required test files in {test_dir}")
        return False
    
    # Check for facts file
    if not facts_path.exists() and not facts_p_path.exists():
        print(f"Error: Missing facts file in {test_dir}")
        return False
    
    print(f"Schema: {schema_path}")
    print(f"Query: {query_path}")
    print(f"Facts: {facts_path if facts_path.exists() else facts_p_path}")
    
    # Generate XSB without demand transformation
    print("\nGenerating XSB without demand transformation...")
    xsb_without_demand = translate_graphql_to_xsb(schema_path, query_path, apply_demand=False)
    without_demand_path = test_dir / "without_demand.P"
    with open(without_demand_path, "w") as f:
        f.write(xsb_without_demand)
    print(f"Output written to {without_demand_path}")
    
    # Generate XSB with demand transformation
    print("\nGenerating XSB with demand transformation...")
    xsb_with_demand = translate_graphql_to_xsb(schema_path, query_path, apply_demand=True)
    with_demand_path = test_dir / "with_demand.P"
    with open(with_demand_path, "w") as f:
        f.write(xsb_with_demand)
    print(f"Output written to {with_demand_path}")
    
    # Prepare facts.P if needed
    if not facts_p_path.exists() and facts_path.exists():
        with open(facts_path, "r") as src, open(facts_p_path, "w") as dest:
            dest.write(src.read())
    
    # Create run files for XSB
    print("\nPreparing files for XSB execution...")
    without_demand_full = test_dir / "run_without_demand.P"
    with_demand_full = test_dir / "run_with_demand.P"
    
    # Determine the appropriate run query based on the XSB output
    # We're using a generic approach to extract results
    with open(without_demand_full, "w") as f:
        f.write(f":- ['facts.P'].\n\n")
        f.write(xsb_without_demand)
        f.write("\n\n% Query to execute\n")
        f.write("% Helper predicate to execute query safely\n")
        f.write("run_safe_query :- catch((ans(X), write('Result: '), write(X), nl, fail), _, (write('Query failed with error'), nl)).\n")
        f.write("run_safe_query :- true.\n\n")
        f.write("% Helper predicate for multi-argument ans\n")
        f.write("show_ans_args(VarList) :- write('Result:'), show_args(VarList).\n")
        f.write("show_args([]) :- nl.\n")
        f.write("show_args([H|T]) :- write(' '), write(H), show_args(T).\n\n")
        f.write("run_query :- (current_predicate(ans/1) -> run_safe_query; ")
        f.write("current_predicate(ans/N), N > 1, functor(Goal, ans, N), ")
        f.write("call(Goal), Goal =.. [_|Args], show_ans_args(Args), fail).\n")
        f.write("run_query :- write('Query completed'), nl.\n")
        f.write("\n:- run_query.\n")
        f.write(":- halt.\n")
    
    with open(with_demand_full, "w") as f:
        f.write(f":- ['facts.P'].\n\n")
        f.write(xsb_with_demand)
        f.write("\n\n% Query to execute\n")
        f.write("% Helper predicate to execute query safely\n")
        f.write("run_safe_query :- catch((ans(X), write('Result: '), write(X), nl, fail), _, (write('Query failed with error'), nl)).\n")
        f.write("run_safe_query :- true.\n\n")
        f.write("% Helper predicate for multi-argument ans\n")
        f.write("show_ans_args(VarList) :- write('Result:'), show_args(VarList).\n")
        f.write("show_args([]) :- nl.\n")
        f.write("show_args([H|T]) :- write(' '), write(H), show_args(T).\n\n")
        f.write("run_query :- (current_predicate(ans/1) -> run_safe_query; ")
        f.write("current_predicate(ans/N), N > 1, functor(Goal, ans, N), ")
        f.write("call(Goal), Goal =.. [_|Args], show_ans_args(Args), fail).\n")
        f.write("run_query :- write('Query completed'), nl.\n")
        f.write("\n:- run_query.\n")
        f.write(":- halt.\n")
    
    # Run XSB queries
    print("\nRunning XSB queries...")
    
    try:
        # Create temporary files for output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as without_demand_output:
            without_demand_out_path = without_demand_output.name
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as with_demand_output:
            with_demand_out_path = with_demand_output.name
        
        # Run XSB
        print("Running XSB without demand transformation...")
        without_demand_cmd = ["xsb", "-e", f"['{without_demand_full}']."]
        subprocess.run(without_demand_cmd, cwd=test_dir, stdout=open(without_demand_out_path, 'w'), check=True)
        
        print("Running XSB with demand transformation...")
        with_demand_cmd = ["xsb", "-e", f"['{with_demand_full}']."]
        subprocess.run(with_demand_cmd, cwd=test_dir, stdout=open(with_demand_out_path, 'w'), check=True)
        
        # Read results
        with open(without_demand_out_path, 'r') as f:
            without_demand_result = f.read().strip()
        
        with open(with_demand_out_path, 'r') as f:
            with_demand_result = f.read().strip()
        
        # Compare results
        print("\nComparing results...")
        if without_demand_result == with_demand_result:
            print("TEST PASSED: Both queries produced the same results!")
            return True
        else:
            print("TEST FAILED: Queries produced different results!")
            print(f"Without demand: {without_demand_result}")
            print(f"With demand: {with_demand_result}")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"Error running XSB: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        # Clean up temporary files
        for path in [without_demand_out_path, with_demand_out_path]:
            if os.path.exists(path):
                os.unlink(path)
        
        # Clean up output files if not keeping them
        if not keep_output:
            for file in ["run_without_demand.P", "run_with_demand.P"]:
                file_path = test_dir / file
                if file_path.exists():
                    os.unlink(file_path)


def run_tests(tests=None, keep_output=False):
    """
    Run the specified tests or all tests if none specified.
    
    Args:
        tests: List of test names to run, or None to run all tests
        keep_output: Whether to keep output files after tests
    
    Returns:
        True if all tests pass, False otherwise
    """
    test_dir = project_root / "tests"
    
    # Get list of all test directories
    all_tests = [d.name for d in test_dir.iterdir() if d.is_dir()]
    
    # If no tests specified, run all tests
    if not tests:
        tests = all_tests
    
    # Filter to only include valid test directories
    valid_tests = [t for t in tests if t in all_tests]
    if not valid_tests:
        print(f"No valid tests found. Available tests: {', '.join(all_tests)}")
        return False
    
    # Run each test
    results = {}
    for test in valid_tests:
        test_path = test_dir / test
        success = run_single_test(test_path, keep_output)
        results[test] = success
    
    # Print summary
    print(f"\n{'='*40}")
    print("Test Summary")
    print(f"{'='*40}")
    
    all_passed = True
    for test, success in results.items():
        status = "PASSED" if success else "FAILED"
        print(f"{test}: {status}")
        all_passed = all_passed and success
    
    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run QueryBridge tests")
    parser.add_argument(
        "tests", nargs="*", 
        help="Names of tests to run (default: all)"
    )
    parser.add_argument(
        "--keep-output", "-k", action="store_true",
        help="Keep output files after tests"
    )
    
    args = parser.parse_args()
    success = run_tests(args.tests, args.keep_output)
    
    sys.exit(0 if success else 1)