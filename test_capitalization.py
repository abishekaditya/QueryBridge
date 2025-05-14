#!/usr/bin/env python3
"""
Test that QueryBridge correctly capitalizes variable names in answer predicates.
"""

import os
import re
import sys
from pathlib import Path

# Add parent directory to path to import QueryBridge
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


def test_capitalization():
    """Test that variable names are properly capitalized in answer predicates."""
    # Use the basic test case for simplicity
    test_dir = project_root / "tests" / "basic"
    schema_path = test_dir / "schema.graphql"
    query_path = test_dir / "query.graphql"
    
    # Generate XSB without demand transformation
    print("\nGenerating XSB without demand transformation...")
    xsb_code = translate_graphql_to_xsb(schema_path, query_path, apply_demand=False)
    
    # Use regex to extract the answer predicate
    ans_pred_match = re.search(r'ans\((.*?)\) :-', xsb_code)
    if ans_pred_match:
        vars_in_head = ans_pred_match.group(1)
        print(f"Variables in answer predicate: {vars_in_head}")
        
        # Check if variables are capitalized
        if vars_in_head.isupper():
            print("TEST PASSED: Variable names are properly capitalized.")
            return True
        else:
            print("TEST FAILED: Variable names are not properly capitalized.")
            print(f"Found: {vars_in_head}")
            print("Expected all uppercase variables.")
            return False
    else:
        print("TEST FAILED: Could not find answer predicate in generated XSB code.")
        return False


if __name__ == "__main__":
    success = test_capitalization()
    sys.exit(0 if success else 1)