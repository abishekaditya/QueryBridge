#!/usr/bin/env python3
"""
tests.py – Run QueryBridge end-to-end tests over every folder inside tests/

For each subfolder in `tests/`, this script will:

1. Locate `schema.graphql`, `query.graphql`, and either `facts.xsb` or `facts.P`.
2. If only `facts.xsb` is present, copy it to `facts.P`.
3. Generate XSB code with and without demand transformation.
4. Produce two Prolog driver files that load `facts.P` and the generated code,
   issue the `ans/...` query, and halt.
5. Invoke XSB on each driver and compare their outputs.
6. Report pass/fail per test and exit nonzero if any fail.

Optional override of the XSB executable via environment variable `XSB_PATH` (defaults to `xsb`).
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from cleanup import clean
import ast
from typing import List

def extract_arrays(text: str) -> List[List[int]]:
    """
    Find all occurrences of “[<digits, optional spaces, commas>]” in the input
    and return them as Python lists of ints.
    """
    # This regex matches any single-level “[<number>(,<number>)*]”
    array_pattern = re.compile(r'\[\s*(?:\d+\s*(?:,\s*\d+)*)\s*\]')
    raw_arrays = array_pattern.findall(text)
    result: List[List[int]] = []
    for arr in raw_arrays:
        # ast.literal_eval turns the string "[65,108,…]" into [65,108,…]
        parsed = ast.literal_eval(arr)
        if isinstance(parsed, list) and all(isinstance(n, int) for n in parsed):
            result.append(parsed)
    return result

def decode_arrays(arrays: List[List[int]]) -> List[str]:
    """
    Given a list of lists of ASCII codes, return their decoded strings.
    """
    return ["".join(chr(code) for code in arr) for arr in arrays]

def extract_and_decode(text: str) -> List[str]:
    """
    Convenience wrapper: from a big text blob, extract all numeric arrays
    and decode each into its ASCII string.
    """
    arrays = extract_arrays(text)
    return decode_arrays(arrays)

# project root and tests folder
project_root = Path(__file__).parent.absolute()
tests_root = project_root / "tests"

# allow overriding XSB binary
XSB = os.environ.get("XSB_PATH", "xsb")

# ensure we can import translate_graphql_to_xsb
sys.path.insert(0, str(project_root))
try:
    from querybridge.translator import translate_graphql_to_xsb
except ImportError:
    sys.path.insert(0, str(project_root / "src"))
    try:
        from querybridge.translator import translate_graphql_to_xsb
    except ImportError:
        print("Error: Could not import `translate_graphql_to_xsb`.")
        print("Make sure you've done `pip install -e .` in the repo root.")
        sys.exit(1)


def run_test_for_dir(test_dir: Path) -> bool:
    print(f"\n=== Running test in {test_dir.name} ===")

    schema = test_dir / "schema.graphql"
    query  = test_dir / "query.graphql"

    # locate facts file (either facts.P or facts.xsb)
    facts_candidates = [test_dir / "facts.P", test_dir / "facts.xsb"]
    facts_src = next((p for p in facts_candidates if p.exists()), None)
    if not (schema.exists() and query.exists() and facts_src):
        print(f"  SKIP: missing schema.graphql, query.graphql, or facts.P/xsb in {test_dir}")
        return True

    facts_p = test_dir / "facts.P"
    if facts_src.name.endswith(".xsb"):
        # copy xsb → P
        facts_p.write_text(facts_src.read_text())
    else:
        # facts_src is already facts.P; no action needed
        pass

    # generate two variants
    print("  Generating XSB (no demand)...", end="", flush=True)
    code_no = translate_graphql_to_xsb(schema, query, apply_demand=False)
    print(" done.")
    print("  Generating XSB (with demand)...", end="", flush=True)
    code_yes = translate_graphql_to_xsb(schema, query, apply_demand=True)
    print(" done.")

    # detect arity of ans/... by regex on the no-demand code
    m = re.search(r"\bans\(([^)]+)\)", code_no)
    if not m:
        print("  ERROR: could not find `ans(...)` in generated code")
        return False
    arity = len(m.group(1).split(","))
    vars_ = [f"V{i}" for i in range(1, arity + 1)]
    var_list = ", ".join(vars_)

    # helper to write a driver file
    def write_driver(name: str, generated_code: str) -> Path:
        driver = test_dir / name
        with driver.open("w") as f:
            f.write(f":- ['facts.P'].\n\n")
            f.write(generated_code)
            f.write("\n\n% execute all answers\n")
            f.write(
                "run_query :- ans("
                + var_list
                + "), write('Result: '), write(["
                + var_list
                + "]), nl, fail.\n"
            )
            f.write("run_query :- write('Query completed.'), nl.\n")
            f.write("\n:- run_query.\n:- halt.\n")
        return driver

    drv_no  = write_driver("run_without_demand.P", code_no)
    drv_yes = write_driver("run_with_demand.P",    code_yes)

    # run XSB on each, capturing stdout
    def exec_xsb(driver: Path) -> str:
        out = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        try:
            subprocess.run(
                [XSB, "-e", f"['{driver.name}']."],
                cwd=test_dir,
                stdout=out,
                stderr=subprocess.PIPE,
                check=True,
            )
            out.flush()
            return Path(out.name).read_text().strip()
        finally:
            out.close()
            os.unlink(out.name)

    try:
        print("  Running XSB (no demand)...", end="", flush=True)
        res_no = exec_xsb(drv_no)
        print(" done.")
        print("  Running XSB (with demand)...", end="", flush=True)
        res_yes = exec_xsb(drv_yes)
        print(" done.")
    except subprocess.CalledProcessError as e:
        print(f"\n  ERROR: XSB failed: {e.stderr.decode().strip()}")
        return False

    # compare
    if res_no == res_yes:
        # print(extract_and_decode(res_no))
        print("   PASS: outputs match")
        return True
    else:
        print("   FAIL: outputs differ")
        print("    -- without demand:\n    " + "\n    ".join(res_no.splitlines()))
        print("    -- with demand:\n    "    + "\n    ".join(res_yes.splitlines()))
        return False


def main():
    if not tests_root.is_dir():
        print("Error: no tests/ folder found")
        sys.exit(1)

    subdirs = [d for d in sorted(tests_root.iterdir()) if d.is_dir()]
    if not subdirs:
        print("Error: tests/ has no subdirectories to run")
        sys.exit(1)

    total = len(subdirs)
    passed = 0
    for d in subdirs:
        if run_test_for_dir(d):
            passed += 1

    print(f"\nSummary: {passed}/{total} tests passed.")
    clean(supress=True)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
