# QueryBridge Module

The QueryBridge module provides functionality to translate GraphQL queries into XSB Datalog queries.

## Main Function

### translateGraphQLtoXSB

```lean
def QueryBridge.translateGraphQLtoXSB (schemaPath : String) (queryPath : String) : IO String
```

Main function to translate GraphQL queries to XSB Datalog.

This function orchestrates the entire translation process:
1. Parses the GraphQL schema file
2. Parses the GraphQL query file
3. Generates XSB Datalog code from the parsed representations

**Parameters:**
- `schemaPath`: Path to the GraphQL schema file
- `queryPath`: Path to the GraphQL query file

**Returns:**
- XSB Datalog code as a string

**Example:**

Given:
- Schema file with a Project type having a tagline field
- Query file requesting the tagline of a project named "GraphQL"

This would return:
```prolog
ans(Tagline) :- project("GraphQL", Tagline).
```