#!/usr/bin/env python3
"""
Cleanup script for QueryBridge tests.

This script cleans up generated files after running tests.
"""

import os
import shutil
import sys
from pathlib import Path


def cleanup_test_directory(test_dir):
    """Clean up generated files in a test directory."""
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
    
    print(f"Cleaning up directory: {test_dir}")
    
    # Remove files matching patterns
    for pattern in patterns:
        for file_path in test_dir.glob(pattern):
            if file_path.name not in files_to_keep:
                try:
                    file_path.unlink()
                    print(f"  Removed: {file_path.name}")
                except Exception as e:
                    print(f"  Error removing {file_path.name}: {e}")


def main():
    """Main function to run the cleanup script."""
    # Get the root directory of the project
    root_dir = Path(__file__).parent
    test_dir = root_dir / "tests"
    test_dir2 = root_dir / "test"
    
    if not test_dir.exists() and not test_dir2.exists():
        print("Error: Test directories not found.")
        return 1
    
    # Clean up test directories
    if test_dir.exists():
        # Clean up subdirectories
        for subdir in test_dir.iterdir():
            if subdir.is_dir():
                cleanup_test_directory(subdir)
    
    if test_dir2.exists():
        # Clean up subdirectories
        for subdir in test_dir2.iterdir():
            if subdir.is_dir():
                cleanup_test_directory(subdir)
    
    # Remove temporary files in the project root
    for temp_file in root_dir.glob("*.xwam"):
        try:
            temp_file.unlink()
            print(f"Removed: {temp_file.name}")
        except Exception as e:
            print(f"Error removing {temp_file.name}: {e}")
    
    print("\nCleanup completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())