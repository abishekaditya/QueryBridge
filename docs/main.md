# Main

CLI interface for the QueryBridge tool.

## Functions and Types

/--
Main function for the QueryBridge CLI.

Translates GraphQL queries to XSB Datalog queries and outputs the result.

# CLI Arguments
- Argument 1: Path to the GraphQL schema file (defaults to "test/basic/schema.graphql")
- Argument 2: Path to the GraphQL query file (defaults to "test/basic/query.graphql")
- Argument 3: Path to the output file (optional)

# Returns
- 0 if successful
- 1 if an error occurred
### Functions

```lean
def main (args : List String) : IO UInt32 := do
```
