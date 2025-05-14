#!/usr/bin/env python3
"""
Test script for QueryBridge with the nested test case.

This script:
1. Generates XSB queries with and without demand transformation
2. Runs both queries against XSB
3. Verifies that both queries produce the same result
"""

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


def run_test():
    """Run the nested test for QueryBridge."""
    # Directory containing test files
    test_dir = project_root / "tests" / "nested"
    schema_path = test_dir / "schema.graphql"
    query_path = test_dir / "query.graphql"
    facts_path = test_dir / "facts.xsb"

    print(f"Running test with files from {test_dir}")
    print(f"Schema: {schema_path}")
    print(f"Query: {query_path}")
    print(f"Facts: {facts_path}")

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

    # Create combined files for execution
    print("\nPreparing files for XSB execution...")
    
    # For consistency, rename facts.xsb to facts.P
    facts_p_path = test_dir / "facts.P"
    if not facts_p_path.exists():
        with open(facts_path, "r") as src, open(facts_p_path, "w") as dest:
            dest.write(src.read())
    
    without_demand_full = test_dir / "run_without_demand.P"
    with open(without_demand_full, "w") as f:
        # Import facts file
        f.write(f":- ['facts.P'].\n\n")
        # Add the generated query
        f.write(xsb_without_demand)
        # Add a query to get results
        f.write("\n\n% Query to execute\n")
        f.write("run_query :- ans(A, B, C, D, E, F), write('Result: '), write(A), write(B), write(C), write(D), write(E), write(F), nl, fail.\n")
        f.write("run_query :- write('Query completed.'), nl.\n")
        f.write("\n:- run_query.\n")
        f.write(":- halt.\n")

    with_demand_full = test_dir / "run_with_demand.P"
    with open(with_demand_full, "w") as f:
        # Import facts file
        f.write(f":- ['facts.P'].\n\n")
        # Add the generated query
        f.write(xsb_with_demand)
        # Add a query to get results
        f.write("\n\n% Query to execute\n")
        f.write("run_query :- ans(A, B, C, D, E, F), write('Result: '), write(A), write(B), write(C), write(D), write(E), write(F), nl, fail.\n")
        f.write("run_query :- write('Query completed.'), nl.\n")
        f.write("\n:- run_query.\n")
        f.write(":- halt.\n")

    # Run the XSB queries and capture the results
    print("\nRunning XSB queries...")
    
    try:
        # Create temporary files for the output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as without_demand_output:
            without_demand_out_path = without_demand_output.name
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as with_demand_output:
            with_demand_out_path = with_demand_output.name
        
        # Run XSB commands
        print("\nRunning XSB without demand transformation...")
        without_demand_cmd = ["xsb", "-e", f"['{without_demand_full}']."]
        subprocess.run(without_demand_cmd, cwd=test_dir, stdout=open(without_demand_out_path, 'w'), check=True)
        
        print("Running XSB with demand transformation...")
        with_demand_cmd = ["xsb", "-e", f"['{with_demand_full}']."]
        subprocess.run(with_demand_cmd, cwd=test_dir, stdout=open(with_demand_out_path, 'w'), check=True)
        
        # Read the results
        with open(without_demand_out_path, 'r') as f:
            without_demand_result = f.read().strip()
        
        with open(with_demand_out_path, 'r') as f:
            with_demand_result = f.read().strip()
        
        # Compare the results
        print("\nComparing results...")
        if without_demand_result == with_demand_result:
            print("TEST PASSED: Both queries produced the same results!")
            print(f"Result: {without_demand_result}")
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


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)