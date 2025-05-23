#!/usr/bin/env python3
"""
Cleanup script for QueryBridge tests.

This script cleans up generated files after running tests.
"""

import sys
from pathlib import Path


def cleanup_test_directory(test_dir, supress):
    """Clean up generated files in a test directory."""
    def log(msg=""):
        if not supress:
            print(msg)
    # Files to remove
    patterns = [
        "*.P",           # All Prolog files except facts.P
        "*.xwam",        # XSB compiled files
        "*.xwam.*",
        "xsb_log.txt",   # XSB log files
        "run_*.P"        # Run files
    ]
    
    # Files to keep
    files_to_keep = [
        "facts.P",
        "schema.graphql",
        "query.graphql",
        "README.md"
    ]
    
    log(f"Cleaning up directory: {test_dir}")
    
    # Remove files matching patterns
    for pattern in patterns:
        for file_path in test_dir.glob(pattern):
            if file_path.name not in files_to_keep:
                try:
                    file_path.unlink()
                    log(f"  Removed: {file_path.name}")
                except Exception as e:
                    log(f"  Error removing {file_path.name}: {e}")



def clean(supress=False):
    """Main function to run the cleanup script."""
    def log(msg=""):
        if not supress:
            print(msg)

    # Get the root directory of the project
    root_dir = Path(__file__).parent
    test_dir  = root_dir / "tests"
    test_dir2 = root_dir / "test"
    
    if not test_dir.exists() and not test_dir2.exists():
        log("Error: Test directories not found.")
        return 1
    
    # Clean up test directories
    for td in (test_dir, test_dir2):
        if td.exists():
            for subdir in td.iterdir():
                if subdir.is_dir():
                    cleanup_test_directory(subdir, supress)
    
    # Remove temporary files in the project root
    for temp_file in root_dir.glob("*.xwam"):
        try:
            temp_file.unlink()
            log(f"Removed: {temp_file.name}")
        except Exception as e:
            log(f"Error removing {temp_file.name}: {e}")
    
    log("\nCleanup completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(clean())