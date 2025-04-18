# Main Module

This module provides the command-line interface for the QueryBridge tool.

## Functions

### main

```lean
def main (args : List String) : IO UInt32
```

Main function for the QueryBridge CLI.

Translates GraphQL queries to XSB Datalog queries and outputs the result.

**CLI Arguments:**
- Argument 1: Path to the GraphQL schema file (defaults to "test/basic/schema.graphql")
- Argument 2: Path to the GraphQL query file (defaults to "test/basic/query.graphql")
- Argument 3: Path to the output file (optional)

**Returns:**
- 0 if successful
- 1 if an error occurred

## Usage

```bash
# Run with default test files
querybridge

# Run with custom files
querybridge path/to/schema.graphql path/to/query.graphql path/to/output.xsb
```

The program will:
1. Parse the GraphQL schema file
2. Parse the GraphQL query file 
3. Generate an XSB Datalog query
4. Output the result to the console
5. Optionally write the result to an output file if specified