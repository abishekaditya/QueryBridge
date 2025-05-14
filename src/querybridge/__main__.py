#!/usr/bin/env python3
"""
Command-line interface for QueryBridge.

This module provides the CLI for translating GraphQL queries to XSB Datalog.
"""

import argparse
import sys
from pathlib import Path

from .translator import translate_graphql_to_xsb


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Translate GraphQL to XSB Datalog with demand transformation"
    )
    
    parser.add_argument("schema_path", 
                        help="Path to the GraphQL schema file")
    
    parser.add_argument("query_path", 
                        help="Path to the GraphQL query file")
    
    parser.add_argument("--output", "-o", 
                        help="Path to write the output file (optional)")
    
    parser.add_argument("--demand", "-d", action="store_true", 
                        help="Apply demand transformation")
    
    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    # Set default schema and query paths if none provided
    if len(sys.argv) == 1:
        sys.argv.extend(["tests/basic/schema.graphql", "tests/basic/query.graphql"])
    
    args = parse_args()
    
    try:
        # Print information about the translation
        print(f"Translating GraphQL to XSB...")
        print(f"Schema: {args.schema_path}")
        print(f"Query: {args.query_path}")
        print(f"Demand Transformation: {'Enabled' if args.demand else 'Disabled'}")
        
        # Run the full translation process
        xsb_code = translate_graphql_to_xsb(args.schema_path, args.query_path, args.demand)
        
        # Print the generated XSB Datalog code
        print("\nGenerated XSB:")
        print(xsb_code)
        
        # Write to output file if specified
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(xsb_code)
            
            print(f"\nOutput written to {args.output}")
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())