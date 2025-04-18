import QueryBridge

/-!
# QueryBridge CLI

Command-line interface for the QueryBridge tool. This program translates GraphQL
queries to XSB Datalog queries.

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
-/

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
-/
def main (args : List String) : IO UInt32 := do
  try
    let schemaPath : String := args.getD 0 "test/basic/schema.graphql"
    let queryPath : String := args.getD 1 "test/basic/query.graphql"
    let outputPath : String := args.getD 2 "output.xsb"
    
    IO.println s!"Translating GraphQL to XSB..."
    IO.println s!"Schema: {schemaPath}"
    IO.println s!"Query: {queryPath}"
    
    let result ← QueryBridge.translateGraphQLtoXSB schemaPath queryPath
    
    IO.println "Generated XSB:"
    IO.println result
    
    if args.length > 2 then
      IO.FS.writeFile outputPath result
      IO.println s!"Output written to {outputPath}"
    
    return 0
  catch e =>
    IO.eprintln s!"Error: {e.toString}"
    return 1
